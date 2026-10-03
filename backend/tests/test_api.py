from io import BytesIO

from docx import Document

from tests.conftest import account

JOB = {
    "title": "Python Engineer",
    "company": "Test Studio",
    "location": "Remote",
    "employment_type": "Full-time",
    "description": "Build thoughtful applications with Python, FastAPI, and PostgreSQL alongside our small engineering team.",
    "salary_min": 100000,
    "salary_max": 140000,
    "skills": ["Python", "FastAPI", "PostgreSQL"],
}


def resume_file():
    doc = Document()
    doc.add_paragraph(
        "Experienced Python engineer building reliable FastAPI services. Skilled in Docker, React, and collaborative product development."
    )
    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def test_auth_rotation_logout_and_role_boundary(client):
    headers = account(client)
    assert client.get("/api/v1/auth/me", headers=headers).json()["role"] == "candidate"
    assert client.post("/api/v1/jobs", headers=headers, json=JOB).status_code == 403
    old_cookie = client.cookies.get("refresh_token")
    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    new_cookie = client.cookies.get("refresh_token")
    client.cookies.clear()
    client.cookies.set("refresh_token", old_cookie)
    assert client.post("/api/v1/auth/refresh").status_code == 401
    client.cookies.clear()
    client.cookies.set("refresh_token", new_cookie)
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_registration_validation_and_duplicate(client):
    account(client)
    payload = {
        "name": "Another",
        "email": "candidate@example.com",
        "password": "a-strong-test-password",
        "role": "candidate",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409
    payload["role"] = "admin"
    assert client.post("/api/v1/auth/register", json=payload).status_code == 422
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "candidate@example.com", "password": "wrong"}
        ).status_code
        == 401
    )


def test_complete_candidate_and_recruiter_flow(client):
    recruiter = account(client, "recruiter@example.com", "recruiter")
    created = client.post("/api/v1/jobs", headers=recruiter, json=JOB)
    assert created.status_code == 201
    job_id = created.json()["id"]
    candidate = account(client)
    uploaded = client.post(
        "/api/v1/resumes",
        headers=candidate,
        files={
            "file": (
                "resume.docx",
                resume_file(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert uploaded.status_code == 201, uploaded.text
    assert "Python" in uploaded.json()["skills"]
    body = {"resume_id": uploaded.json()["id"], "job_id": job_id}
    matched = client.post("/api/v1/matches", headers=candidate, json=body)
    assert matched.status_code == 200, matched.text
    assert matched.json()["method"] == "keyword"
    assert matched.json()["score"] == 40.0
    assert matched.json()["confidence"] == "low"
    assert matched.json()["confidence_label"] == "Low confidence"
    assert matched.json()["missing"] == ["PostgreSQL"]
    assert client.post("/api/v1/matches", headers=candidate, json=body).status_code == 200
    application = client.post("/api/v1/applications", headers=candidate, json=body)
    assert application.status_code == 201
    assert client.post("/api/v1/applications", headers=candidate, json=body).status_code == 409
    ranked = client.get("/api/v1/applications", headers=recruiter).json()
    assert ranked[0]["score"] == 40.0
    assert (
        client.patch(
            f"/api/v1/applications/{application.json()['id']}",
            headers=recruiter,
            json={"status": "Interview"},
        ).status_code
        == 200
    )
    analytics = client.get("/api/v1/analytics", headers=candidate).json()
    assert analytics["interviews"] == 1
    assert analytics["skill_gaps"] == {"PostgreSQL": 1}
    other = account(client, "other@example.com")
    assert client.post("/api/v1/matches", headers=other, json=body).status_code == 404
    assert client.delete(f"/api/v1/resumes/{body['resume_id']}", headers=other).status_code == 404
    assert client.delete(f"/api/v1/resumes/{body['resume_id']}", headers=candidate).status_code == 204
    remaining = client.get("/api/v1/applications", headers=candidate).json()
    assert len(remaining) == 1 and remaining[0]["score"] is None  # Tracker history survives resume deletion.


def test_job_search_ownership_and_archive(client):
    recruiter = account(client, "owner@example.com", "recruiter")
    job_id = client.post("/api/v1/jobs", headers=recruiter, json=JOB).json()["id"]
    other = account(client, "other@example.com", "recruiter")
    assert client.put(f"/api/v1/jobs/{job_id}", headers=other, json=JOB).status_code == 403
    assert client.delete(f"/api/v1/jobs/{job_id}", headers=other).status_code == 403
    assert client.get("/api/v1/jobs?q=python&location=Remote").json()["total"] == 1
    assert client.get("/api/v1/jobs?q=unrelated").json()["total"] == 0
    assert client.get("/api/v1/jobs?page=0").status_code == 422
    assert (
        client.put(f"/api/v1/jobs/{job_id}", headers=recruiter, json={**JOB, "salary_max": 1}).status_code
        == 422
    )
    assert client.delete(f"/api/v1/jobs/{job_id}", headers=recruiter).status_code == 204
    assert client.get(f"/api/v1/jobs/{job_id}").status_code == 404


def test_invalid_files_and_admin_access(client):
    headers = account(client)
    assert client.get("/api/v1/admin", headers=headers).status_code == 403
    assert client.get("/api/v1/resumes").status_code == 401
    for filename, data, status in [
        ("cv.txt", b"plain text", 415),
        ("cv.pdf", b"not a PDF", 415),
        ("cv.docx", b"PKbroken", 422),
        ("empty.pdf", b"", 413),
        ("large.pdf", b"%PDF-" + b"x" * (5 * 1024 * 1024), 413),
    ]:
        response = client.post("/api/v1/resumes", headers=headers, files={"file": (filename, data)})
        assert response.status_code == status, response.text


def test_refresh_rejects_untrusted_origin(client):
    account(client)
    assert (
        client.post("/api/v1/auth/refresh", headers={"Origin": "https://untrusted.example"}).status_code
        == 403
    )

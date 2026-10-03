"""Comprehensive end-to-end tests for Career Assistant backend, intent parsing,
savepoint transaction safety, guardrails, and citation integrity.
"""

from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import ChatMessage, Job, LearningResource, MatchResult, Resume, Skill, User
from app.services.assistant import (
    CareerAssistant,
    RetrieveResumeContextArgs,
    SearchJobsArgs,
    friendly_tool_error,
)
from app.services.nl_search import coerce_bool, parse_nl_query_heuristic


# --- Unit Tests ---


def test_tool_arg_coercion():
    """Verify tool args coercion converts strings/ints/variants into bools and limits."""
    # Boolean coercion
    assert coerce_bool("true") is True
    assert coerce_bool("True") is True
    assert coerce_bool("yes") is True
    assert coerce_bool("1") is True
    assert coerce_bool(1) is True
    assert coerce_bool(True) is True

    assert coerce_bool("false") is False
    assert coerce_bool("no") is False
    assert coerce_bool("0") is False
    assert coerce_bool(0) is False
    assert coerce_bool(False) is False
    assert coerce_bool(None) is None
    assert coerce_bool("") is None

    # SearchJobsArgs Pydantic model coercion
    args1 = SearchJobsArgs(query="Python dev", remote="true", experience_level="internship", limit="5")
    assert args1.q == "Python dev"
    assert args1.remote is True
    assert args1.experience_level == "intern"
    assert args1.limit == 5

    args2 = SearchJobsArgs(q="React", remote="no", experience_level="entry-level", limit=None)
    assert args2.remote is False
    assert args2.experience_level == "entry"
    assert args2.limit == 10

    args3 = SearchJobsArgs(q="Architect", experience_level="lead")
    assert args3.experience_level == "senior"


def test_retrieve_resume_context_defaults():
    """Verify retrieve_resume_context args model defaults top_k to 4."""
    args = RetrieveResumeContextArgs(query="Kubernetes experience")
    assert args.top_k == 4
    assert args.query == "Kubernetes experience"

    # When None or empty string is passed for top_k
    args_none = RetrieveResumeContextArgs(query="Docker", top_k=None)
    assert args_none.top_k == 4

    # When string number is passed
    args_str = RetrieveResumeContextArgs(query="Docker", top_k="8")
    assert args_str.top_k == 8


def test_intent_mapping_10_sample_queries():
    """Verify intent mapping accurately extracts filters and strips intent keywords."""
    queries = [
        # 1. Remote python internships
        ("Search remote Python internships", "intern", True, None, False, "Python"),
        # 2. Fresher frontend developer
        ("Looking for fresher frontend developer jobs", "entry", None, None, False, "frontend developer"),
        # 3. Senior backend engineer in United States
        ("Senior backend engineer in United States", "senior", None, "United States", False, "backend engineer"),
        # 4. Entry-level data scientist onsite
        ("Entry-level data scientist onsite", "entry", False, None, False, "data scientist"),
        # 5. Remote Golang roles
        ("Remote Golang roles", None, True, None, False, "Golang"),
        # 6. Intern machine learning engineer
        ("Intern machine learning engineer", "intern", None, None, False, "machine learning engineer"),
        # 7. Junior devops openings in Germany
        ("Junior devops openings in Germany", "entry", None, "Germany", False, "devops"),
        # 8. Lead architect roles paying salary
        ("Lead architect roles paying salary", "senior", None, None, True, "architect"),
        # 9. Mid-level React developer
        ("Mid-level React developer", "mid", None, None, False, "React developer"),
        # 10. General search for full stack engineer
        ("Show me jobs for full stack engineer", None, None, None, False, "full stack engineer"),
    ]

    for q, exp_level, remote, country, sal_disc, expected_kw in queries:
        parsed = parse_nl_query_heuristic(q)
        if exp_level is not None:
            assert parsed["experience_level"] == exp_level, f"Failed exp_level for '{q}'"
        if remote is not None:
            assert parsed["remote"] is remote, f"Failed remote for '{q}'"
        if country is not None:
            assert parsed["country"] == country, f"Failed country for '{q}'"
        assert parsed["salary_disclosed"] is sal_disc, f"Failed salary_disclosed for '{q}'"
        assert expected_kw.casefold() in parsed["q"].casefold(), f"Keyword '{expected_kw}' missing in '{parsed['q']}'"


@pytest.fixture
def test_db():
    """Isolated in-memory SQLite database session for unit/integration testing."""
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_search_jobs_with_remote_and_intern(test_db: Session):
    """Verify search_jobs executes with real bool and without SQL errors."""
    u = User(name="Test Candidate", email="cand@example.com", password_hash="hash", role="candidate")
    test_db.add(u)
    test_db.flush()

    job1 = Job(
        title="Python Software Intern",
        company="TechCorp",
        location="Remote",
        country="United States",
        remote=True,
        experience_level="intern",
        active=True,
        description="Write Python backend code",
    )
    test_db.add(job1)
    test_db.commit()

    assistant = CareerAssistant(test_db, u, None)
    # Call with string-like args coerced via search_jobs
    res = assistant.tool_search_jobs(query="Python", remote=True, experience_level="intern")
    assert len(res) >= 1
    assert res[0]["job_id"] == job1.id
    assert res[0]["remote"] is True


def test_savepoint_rollback_leaves_session_usable(test_db: Session):
    """Verify that a tool error handled in a savepoint (begin_nested) leaves the session fully usable."""
    u = User(name="Safe User", email="safe@example.com", password_hash="hash", role="candidate")
    test_db.add(u)
    test_db.commit()

    assistant = CareerAssistant(test_db, u, None)

    # Dispatch tool with invalid data that triggers a tool failure inside savepoint
    tool_out = assistant._execute_tool_with_savepoint("unknown_tool", {})
    assert tool_out["ok"] is False

    # Session must NOT be poisoned: we can query and commit immediately
    user_check = test_db.scalar(select(User).where(User.id == u.id))
    assert user_check is not None
    assert user_check.name == "Safe User"

    # Add a new record to verify write transactions succeed after savepoint rollback
    j = Job(title="DevOps Engineer", company="InfraCo", location="Bangalore", active=True, description="Manage infrastructure")
    test_db.add(j)
    test_db.commit()
    assert j.id is not None


def test_citation_stripping():
    """Verify that unverified [Job #id] citations not returned this turn are stripped."""
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        u = User(name="Cite User", email="cite@example.com", password_hash="hash", role="candidate")
        session.add(u)
        j10 = Job(id=10, title="Real Job 10", company="C10", location="Remote", active=True, description="Real job description")
        session.add(j10)
        session.commit()

        assistant = CareerAssistant(session, u, None)

        step1 = {
            "content": "",
            "tool_calls": [{"id": "c1", "name": "search_jobs", "args": {"q": "Real"}}],
            "provider": "groq",
        }
        step2 = {
            "content": "Check out [Job #10] which matches your skills. Also consider [Job #999].",
            "tool_calls": [],
            "provider": "groq",
        }

        with patch.object(assistant.ai, "chat_step", side_effect=[step1, step2]):
            with patch.object(
                assistant,
                "_execute_tool_with_savepoint",
                return_value={"ok": True, "result": {"jobs": [{"job_id": 10, "citation": "[Job #10]"}]}},
            ):
                res = assistant.process_message("Show me jobs")
                assert "[Job #10]" in res["reply"]
                assert "[Job #999]" not in res["reply"]


# --- Integration Tests (LLM Mocked) ---


def test_search_remote_python_internships_relaxed_filter(test_db: Session):
    """Verify 'Search remote Python internships' returns jobs or friendly relaxed-filter message."""
    u = User(name="Python Intern", email="pyintern@example.com", password_hash="hash", role="candidate")
    test_db.add(u)

    # Add an onsite Python internship (remote=False) to test relaxation
    job = Job(
        title="Python Software Engineering Intern",
        company="PyCorp",
        location="Berlin, Germany",
        country="Germany",
        remote=False,
        experience_level="intern",
        active=True,
        description="Python development",
    )
    test_db.add(job)
    test_db.commit()

    assistant = CareerAssistant(test_db, u, None)

    # Query with remote=True, experience_level="intern"
    res = assistant.tool_search_jobs(query="Python", remote=True, experience_level="intern")
    assert res["count"] >= 1
    # Filter was relaxed because 0 remote jobs existed
    assert "No remote" in res["relaxed_note"]
    assert res["jobs"][0]["job_id"] == job.id


def test_how_do_i_learn_docker_no_tool_or_json_words(test_db: Session):
    """Verify 'How do I learn Docker?' returns roadmap + curated link and NEVER contains 'tool' or 'JSON'."""
    u = User(name="Learner", email="learner@example.com", password_hash="hash", role="candidate")
    test_db.add(u)
    skill = Skill(name="Docker")
    test_db.add(skill)
    test_db.flush()

    resource = LearningResource(
        skill_id=skill.id,
        title="Docker Official Getting Started Guide",
        url="https://docs.docker.com/get-started/",
        provider="Docker Official",
    )
    test_db.add(resource)
    test_db.commit()

    assistant = CareerAssistant(test_db, u, None)

    # Mock chat_step to generate a clean response
    mock_reply = (
        "Here is a structured roadmap to learn Docker:\n"
        "1. Understand Container Concepts: learn the difference between containers and VMs.\n"
        "2. Dockerfile Basics: write instructions to build container images.\n"
        "3. Networking and Volumes: persist application data and connect containers.\n"
        "4. Docker Compose: orchestrate multi-container services.\n\n"
        "Curated Guide: [Docker Official Getting Started Guide](https://docs.docker.com/get-started/)"
    )

    with patch.object(assistant.ai, "chat_step", return_value={"content": mock_reply, "tool_calls": [], "provider": "groq"}):
        res = assistant.process_message("How do I learn Docker?")
        reply = res["reply"]
        assert "roadmap" in reply.casefold() or "docker" in reply.casefold()
        assert "https://docs.docker.com" in reply
        # Verify the words "tool" and "json" never appear in user-facing reply
        assert "tool" not in reply.casefold()
        assert "json" not in reply.casefold()


def test_failing_tool_gives_friendly_message_and_persists_memory(test_db: Session):
    """Verify that when a tool fails, user receives a friendly sentence and chat memory is persisted."""
    u = User(name="Resilient User", email="resilient@example.com", password_hash="hash", role="candidate")
    test_db.add(u)
    test_db.commit()

    assistant = CareerAssistant(test_db, u, None)

    # Force search_jobs to raise an exception inside the tool execution
    with patch.object(assistant, "tool_search_jobs", side_effect=RuntimeError("Database connection dropped")):
        # Mock step that tries to call search_jobs
        call_step = {
            "content": "",
            "tool_calls": [{"id": "c1", "name": "search_jobs", "args": {"q": "Python"}}],
            "provider": "groq",
        }
        with patch.object(assistant.ai, "chat_step", return_value=call_step):
            res = assistant.process_message("Search Python jobs")
            reply = res["reply"]

            # Must never expose traceback or raw internal error
            assert "RuntimeError" not in reply
            assert "Database connection dropped" not in reply
            # Must match friendly message
            assert "couldn't search jobs just now" in reply or "Find jobs" in reply

            # Verify chat memory was successfully persisted in the database
            messages = list(test_db.scalars(select(ChatMessage).where(ChatMessage.user_id == u.id)).all())
            assert len(messages) >= 2
            assert messages[0].role == "user"
            assert messages[1].role == "assistant"
            assert messages[1].content == reply


def test_assistant_context_with_candidate_resume(test_db):
    from app.routers.ai import assistant_context

    u = User(name="Context Candidate", email="ctx@test.com", password_hash="hash", role="candidate")
    test_db.add(u)
    test_db.commit()

    # Create active resume
    r = Resume(user_id=u.id, filename="my_sample_resume.pdf", text="Python FastAPI React", is_primary=True, experience_years=3.5)
    test_db.add(r)
    test_db.commit()

    ctx = assistant_context(test_db, u)
    assert ctx["has_resume"] is True
    assert ctx["resume_filename"] == "my_sample_resume.pdf"
    assert ctx["experience_years"] == 3.5
    assert ctx["candidate_name"] == "Context Candidate"
    assert len(ctx["suggested_prompts"]) > 0


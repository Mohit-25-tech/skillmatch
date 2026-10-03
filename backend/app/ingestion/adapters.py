"""Official APIs only. No employer-page, LinkedIn, Indeed, or Naukri scraping."""

import re
from abc import ABC, abstractmethod

from app.config import get_settings
from app.ingestion.http import FeedError, FeedHTTP
from app.ingestion.normalization import RawJob, plain_text, salary_text, timestamp


def slug(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", value):
        raise FeedError("Invalid company slug")
    return value


class Adapter(ABC):
    complete = False

    def __init__(self, http: FeedHTTP, config: dict):
        self.http, self.config = http, config
        self.complete = False

    @abstractmethod
    def fetch(self) -> list[RawJob]:
        """Return a validated snapshot; set complete only after every page succeeds."""
        raise NotImplementedError


class GreenhouseAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        company = slug(self.config["slug"])
        body = self.http.get(
            f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs", {"content": "true"}
        )
        if not isinstance(body, dict) or not isinstance(body.get("jobs"), list):
            raise FeedError("Invalid Greenhouse feed")
        jobs = []
        for row in body["jobs"]:
            location = row.get("location", {}).get("name") or "Not specified"
            text = plain_text(row.get("content", ""))
            jobs.append(
                RawJob(
                    external_id=str(row["id"]),
                    title=row["title"],
                    company=self.config.get("company", company),
                    location=location[:100],
                    remote="remote" in location.lower(),
                    description=text,
                    apply_url=row["absolute_url"],
                    posted_at=timestamp(row.get("first_published")),
                    attribution="Greenhouse",
                    attribution_url=row["absolute_url"],
                    **salary_text(text),
                )
            )
        self.complete = True
        return jobs


class LeverAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        company = slug(self.config["slug"])
        host = "api.eu.lever.co" if self.config.get("region") == "eu" else "api.lever.co"
        jobs = []
        for page in range(get_settings().ingestion_max_pages):
            body = self.http.get(
                f"https://{host}/v0/postings/{company}", {"mode": "json", "skip": page * 100, "limit": 100}
            )
            if not isinstance(body, list):
                raise FeedError("Invalid Lever feed")
            for row in body:
                cats = row.get("categories") or {}
                pay = row.get("salaryRange") or {}
                text = (
                    (row.get("descriptionPlain") or row.get("description", ""))
                    + "\n"
                    + "\n".join(
                        str(x.get("text", "")) + "\n" + x.get("content", "") for x in row.get("lists", [])
                    )
                )
                jobs.append(
                    RawJob(
                        external_id=row["id"],
                        title=row["text"],
                        company=self.config.get("company", company),
                        location=(cats.get("location") or "Not specified")[:100],
                        remote=bool(
                            row.get("workplaceType") == "remote"
                            or cats.get("workplaceType") == "remote"
                            or "remote" in (cats.get("location") or "").lower()
                        ),
                        employment_type=cats.get("commitment") or "Not specified",
                        description=text,
                        apply_url=row.get("applyUrl") or row["hostedUrl"],
                        posted_at=timestamp(row.get("createdAt")),
                        salary_min=round(pay["min"]) if pay.get("min") is not None else None,
                        salary_max=round(pay["max"]) if pay.get("max") is not None else None,
                        salary_currency=pay.get("currency"),
                        salary_interval=pay.get("interval"),
                        attribution="Lever",
                        attribution_url=row["hostedUrl"],
                    )
                )
            if len(body) < 100:
                self.complete = True
                break
        return jobs


class AshbyAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        board = slug(self.config["slug"])
        body = self.http.get(
            f"https://api.ashbyhq.com/posting-api/job-board/{board}",
            {"includeCompensation": "true"},
        )
        if not isinstance(body, dict) or not isinstance(body.get("jobs"), list):
            raise FeedError("Invalid Ashby feed")
        jobs = []
        for row in body["jobs"]:
            if row.get("isListed") is not True:
                continue
            # Use only the publisher's summary salary, not equity or guessed units.
            salaries = [
                c
                for c in (row.get("compensation") or {}).get("summaryComponents", [])
                if c.get("compensationType") == "Salary"
            ]
            pay = salaries[0] if len(salaries) == 1 else {}
            jobs.append(
                RawJob(
                    external_id=row.get("id") or row["jobUrl"].rstrip("/").rsplit("/", 1)[-1],
                    title=row["title"],
                    company=self.config.get("company", board),
                    location=(row.get("location") or "Not specified")[:100],
                    remote=bool(
                        row.get("isRemote")
                        or row.get("workplaceType") == "Remote"
                        or "remote" in (row.get("location") or "").lower()
                    ),
                    employment_type=row.get("employmentType") or "Not specified",
                    description=row.get("descriptionPlain") or row.get("descriptionHtml") or "",
                    apply_url=row.get("applyUrl") or row["jobUrl"],
                    posted_at=timestamp(row.get("publishedAt")),
                    salary_min=round(pay["minValue"]) if pay.get("minValue") is not None else None,
                    salary_max=round(pay["maxValue"]) if pay.get("maxValue") is not None else None,
                    salary_currency=pay.get("currencyCode"),
                    salary_interval={"1 YEAR": "year", "1 MONTH": "month", "1 HOUR": "hour"}.get(
                        pay.get("interval")
                    ),
                    attribution="Ashby",
                    attribution_url=row["jobUrl"],
                )
            )
        self.complete = True
        return jobs


class RemotiveAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        body = self.http.get("https://remotive.com/api/remote-jobs")
        if not isinstance(body, dict) or not isinstance(body.get("jobs"), list):
            raise FeedError("Invalid Remotive feed")
        result = [
            RawJob(
                external_id=str(r["id"]),
                title=r["title"],
                company=r["company_name"],
                location=(r.get("candidate_required_location") or "Not specified")[:100],
                remote=True,
                employment_type=r.get("job_type") or "Not specified",
                description=r["description"],
                apply_url=r["url"],
                posted_at=timestamp(r.get("publication_date")),
                attribution="Remotive",
                attribution_url=r["url"],
                **salary_text(r.get("salary", "")),
            )
            for r in body["jobs"]
        ]
        self.complete = True
        return result


class ArbeitnowAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        jobs = []
        for page in range(1, get_settings().ingestion_max_pages + 1):
            body = self.http.get("https://www.arbeitnow.com/api/job-board-api", {"page": page})
            if not isinstance(body, dict) or not isinstance(body.get("data"), list):
                raise FeedError("Invalid Arbeitnow feed")
            for r in body["data"]:
                jobs.append(
                    RawJob(
                        external_id=r["slug"],
                        title=r["title"],
                        company=r["company_name"],
                        location=(r.get("location") or "Not specified")[:100],
                        remote=bool(
                            r.get("remote") or "remote" in (r.get("location") or "").lower()
                        ),
                        employment_type=",".join(r.get("job_types", [])) or "Not specified",
                        description=r["description"],
                        apply_url=r["url"],
                        posted_at=timestamp(r.get("created_at")),
                        attribution="Arbeitnow",
                        attribution_url=r["url"],
                    )
                )
            if not body.get("links", {}).get("next"):
                self.complete = True
                break
        return jobs


class RemoteOKAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        body = self.http.get("https://remoteok.com/api")
        if not isinstance(body, list) or not body or not isinstance(body[0], dict) or "legal" not in body[0]:
            raise FeedError("Invalid Remote OK feed or missing attribution terms")
        jobs = []
        for r in body[1:]:
            jobs.append(
                RawJob(
                    external_id=str(r["id"]),
                    title=r["position"],
                    company=r["company"],
                    location=(r.get("location") or "Not specified")[:100],
                    remote=True,
                    description=r["description"],
                    apply_url=r["url"],
                    posted_at=timestamp(r.get("date") or r.get("epoch")),
                    salary_min=r.get("salary_min") or None,
                    salary_max=r.get("salary_max") or None,
                    salary_currency=r.get("salary_currency"),
                    salary_interval="year" if r.get("salary_min") else None,
                    attribution="Remote OK",
                    attribution_url=r["url"],
                )
            )
        self.complete = True
        return jobs


class AdzunaAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        settings = get_settings()
        if (
            not settings.adzuna_app_id
            or not settings.adzuna_app_key
            or "PLACEHOLDER" in settings.adzuna_app_key
        ):
            raise FeedError("Configure ADZUNA_APP_ID and ADZUNA_APP_KEY")
        country = self.config.get("country", "in").lower()
        if country not in {
            "in",
            "gb",
            "us",
            "au",
            "at",
            "be",
            "br",
            "ca",
            "ch",
            "de",
            "es",
            "fr",
            "it",
            "mx",
            "nl",
            "nz",
            "pl",
            "sg",
            "za",
        }:
            raise FeedError("Unsupported Adzuna country")
        jobs = []
        for page in range(1, settings.ingestion_max_pages + 1):
            body = self.http.get(
                f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}",
                {
                    "app_id": settings.adzuna_app_id,
                    "app_key": settings.adzuna_app_key,
                    "results_per_page": 50,
                    "what": self.config.get("query", ""),
                    "content-type": "application/json",
                },
            )
            if not isinstance(body, dict) or not isinstance(body.get("results"), list):
                raise FeedError("Invalid Adzuna feed")
            for r in body["results"]:
                actual = str(r.get("salary_is_predicted", "1")) == "0"
                jobs.append(
                    RawJob(
                        external_id=str(r["id"]),
                        title=plain_text(r["title"]),
                        company=r.get("company", {}).get("display_name", "Not specified"),
                        location=r.get("location", {}).get("display_name", "Not specified")[:100],
                        remote=bool(re.search(r"\bremote\b", r["title"], re.I)),
                        employment_type=r.get("contract_time", "Not specified").replace("_", "-"),
                        description=r["description"],
                        apply_url=r["redirect_url"],
                        posted_at=timestamp(r.get("created")),
                        salary_min=round(r["salary_min"])
                        if actual and r.get("salary_min") is not None
                        else None,
                        salary_max=round(r["salary_max"])
                        if actual and r.get("salary_max") is not None
                        else None,
                        salary_currency=r.get("salary_currency"),
                        salary_interval="year" if actual and r.get("salary_min") is not None else None,
                        attribution="Adzuna",
                        attribution_url=r["redirect_url"],
                    )
                )
            if len(body["results"]) < 50 or len(jobs) >= body.get("count", float("inf")):
                self.complete = True
                break
        return jobs


class HackerNewsAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        thread_id = int(self.config["thread_id"])
        parent = self.http.get(f"https://hacker-news.firebaseio.com/v0/item/{thread_id}.json")
        if (
            not parent
            or "who is hiring" not in parent.get("title", "").lower()
            or parent.get("by") != "whoishiring"
        ):
            raise FeedError("Configure an official Who is hiring thread ID")
        jobs = []
        ids = parent.get("kids", [])
        limit = int(self.config.get("max_comments", 200))
        for item_id in ids[:limit]:
            row = self.http.get(f"https://hacker-news.firebaseio.com/v0/item/{int(item_id)}.json")
            if not row or row.get("deleted") or row.get("dead") or not row.get("text"):
                continue
            description = plain_text(row["text"])
            first = description.split("\n")[0]
            company = first.split("|")[0].strip()[:100] or "Not specified"
            url = f"https://news.ycombinator.com/item?id={item_id}"
            jobs.append(
                RawJob(
                    external_id=str(item_id),
                    title=first[:150],
                    company=company,
                    description=description,
                    remote=bool(re.search(r"\bremote\b", first, re.I)),
                    apply_url=url,
                    posted_at=timestamp(row.get("time")),
                    attribution="Hacker News — Who is hiring",
                    attribution_url=url,
                    **salary_text(description),
                )
            )
        # A discussion is not an authoritative active-jobs inventory; never close from disappearance.
        self.complete = False
        return jobs


ADAPTERS = {
    "ashby": AshbyAdapter,
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "remotive": RemotiveAdapter,
    "arbeitnow": ArbeitnowAdapter,
    "remoteok": RemoteOKAdapter,
    "adzuna": AdzunaAdapter,
    "hackernews": HackerNewsAdapter,
}

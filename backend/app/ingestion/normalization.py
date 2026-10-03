import hashlib
import html
import re
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.blocked = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "iframe", "object"}:
            self.blocked += 1
        if tag in {"p", "br", "li", "div", "h1", "h2", "h3"} and not self.blocked:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "iframe", "object"}:
            self.blocked = max(0, self.blocked - 1)
        if tag in {"p", "li", "div"} and not self.blocked:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.blocked:
            self.parts.append(data)


def plain_text(value: str) -> str:
    parser = TextParser()
    parser.feed(html.unescape(value or ""))
    return re.sub(r"\n\s*\n+", "\n\n", "".join(parser.parts)).strip()[:100000]


def safe_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme not in {"https", "http"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("A public HTTP(S) apply URL is required")
    return value


def timestamp(value) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000 if value > 10**11 else value, timezone.utc)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def normalized(value: str) -> str:
    return " ".join(sorted(re.findall(r"[\w+#]+", unicodedata.normalize("NFKC", value).casefold())))


def fingerprint(title: str, company: str, location: str) -> str:
    return hashlib.sha256("|".join(normalized(v) for v in (title, company, location)).encode()).hexdigest()


def salary_text(value: str) -> dict:
    """Only explicit two-ended ranges with an identifiable currency; never estimate."""
    match = re.search(
        r"(?P<c>USD|EUR|GBP|INR|US\$|€|£|₹)\s*(?P<lo>[\d,.]+)\s*(?P<lk>[kK]?)\s*[-–—]\s*(?:USD|EUR|GBP|INR|US\$|€|£|₹)?\s*(?P<hi>[\d,.]+)\s*(?P<hk>[kK]?)",
        value or "",
        re.I,
    )
    if not match:
        return {}
    currency = {"US$": "USD", "€": "EUR", "£": "GBP", "₹": "INR"}.get(match["c"].upper(), match["c"].upper())
    low = float(match["lo"].replace(",", "")) * (1000 if match["lk"] or match["hk"] else 1)
    high = float(match["hi"].replace(",", "")) * (1000 if match["hk"] else 1)
    if not 0 < low <= high <= 100000000:
        return {}
    period = next(
        (
            p
            for p, pattern in [
                ("hour", r"hour|hourly"),
                ("month", r"month|monthly"),
                ("year", r"year|annual|annum"),
            ]
            if re.search(pattern, value, re.I)
        ),
        None,
    )
    return dict(
        salary_min=round(low), salary_max=round(high), salary_currency=currency, salary_interval=period
    )


def normalize_location(value: str, is_remote: bool = False) -> str:
    """Standardize city/state/country and Remote – region representations."""
    if not value or value.strip().casefold() in {"", "not specified", "null", "none"}:
        return "Remote" if is_remote else "Not specified"
    cleaned = re.sub(r"\s+", " ", value.strip())
    cleaned = re.sub(r"\s*[-–—]\s*", " – ", cleaned)
    remote_match = re.search(r"\bremote\b(?:\s*–\s*|\s*\(|\s+in\s+)?([^)]*)", cleaned, re.I)
    if is_remote or remote_match:
        region = (remote_match.group(1).rstrip(")").strip() if remote_match else "").strip(" –")
        if not region or region.casefold() in {"worldwide", "anywhere", "global", "yes", "true", "remote"}:
            return "Remote"
        if region.casefold() in {"us", "usa", "united states", "north america"}:
            return "Remote – US"
        if region.casefold() in {"uk", "united kingdom", "great britain"}:
            return "Remote – UK"
        if region.casefold() in {"eu", "europe"}:
            return "Remote – Europe"
        if region.casefold() in {"in", "india"}:
            return "Remote – India"
        tokens = [
            part.upper()
            if part.upper() in {"EMEA", "APAC", "UK", "US", "USA", "EU", "LATAM", "LATAM/CARIBBEAN"}
            else part.title()
            for part in re.split(r"(\s+|/)", region)
        ]
        return f"Remote – {''.join(tokens)}"
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
    formatted = []
    for part in parts:
        if len(part) == 2 and part.isalpha():
            formatted.append(part.upper())
        elif part.upper() in {"USA", "UK", "UAE", "EU", "APAC", "EMEA"}:
            formatted.append(part.upper())
        else:
            formatted.append(part.title())
    return ", ".join(formatted) if formatted else "Not specified"


INDIA_LOCATIONS = {
    "india", "bangalore", "bengaluru", "hyderabad", "pune", "mumbai", "delhi", "gurgaon", "gurugram",
    "noida", "chennai", "kolkata", "ahmedabad", "jaipur", "kochi", "coimbatore", "indore"
}


def infer_experience_level(title: str, description: str = "", experience_min: float | None = None) -> str:
    title_cf = (title or "").casefold()
    desc_cf = (description or "")[:2000].casefold()
    if any(k in title_cf for k in ["intern", "co-op", "trainee", "student"]):
        return "intern"
    if any(k in title_cf for k in ["senior", "sr.", "principal", "lead", "staff", "architect", "head of", "director"]):
        return "senior"
    if experience_min is not None and experience_min >= 5.0:
        return "senior"
    if any(k in title_cf for k in ["junior", "jr.", "entry", "associate", "graduate", "new grad", "fresher"]) or (
        experience_min is not None and experience_min <= 1.0
    ):
        return "entry"
    if any(k in desc_cf for k in ["0-1 year", "0 to 1 year", "entry level", "new graduates", "no experience required"]):
        return "entry"
    if experience_min is not None and 1.0 < experience_min < 5.0:
        return "mid"
    return "mid"


def infer_country(location: str) -> str | None:
    if not location:
        return None
    loc_cf = location.casefold()
    if any(city in loc_cf for city in INDIA_LOCATIONS):
        return "India"
    if any(p in loc_cf for p in ["united states", "usa", "san francisco", "new york", "seattle", "austin", "chicago"]):
        return "United States"
    if any(p in loc_cf for p in ["united kingdom", "london", "manchester", "uk"]):
        return "United Kingdom"
    if any(p in loc_cf for p in ["germany", "berlin", "munich"]):
        return "Germany"
    if any(p in loc_cf for p in ["canada", "toronto", "vancouver"]):
        return "Canada"
    if "remote" in loc_cf:
        return "Remote"
    return None


class RawJob(BaseModel):
    external_id: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=150)
    company: str = Field(min_length=1, max_length=100)
    location: str = Field(default="Not specified", max_length=150)
    remote: bool = False
    employment_type: str = "Not specified"
    experience_level: str | None = None
    country: str | None = None
    description: str
    apply_url: str
    posted_at: datetime | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_currency: str | None = None
    salary_interval: str | None = None
    attribution: str
    attribution_url: str

    _urls = field_validator("apply_url", "attribution_url")(safe_url)
    _description = field_validator("description", mode="before")(plain_text)

    @field_validator("employment_type", mode="before")
    @classmethod
    def job_type(cls, value):
        key = str(value or "").lower().replace("_", "-").replace(" ", "-")
        return {
            "full-time": "Full-time",
            "fulltime": "Full-time",
            "part-time": "Part-time",
            "parttime": "Part-time",
            "intern": "Internship",
            "contract": "Contract",
            "contractor": "Contract",
            "internship": "Internship",
        }.get(key, str(value or "Not specified")[:30])

    @model_validator(mode="after")
    def validate_salary(self):
        loc_text = f"{self.location or ''} {self.title or ''}".casefold()
        if not self.remote and any(
            k in loc_text for k in ["remote", "anywhere", "work from home", "wfh", "telecommute", "distributed"]
        ):
            self.remote = True
        self.location = normalize_location(self.location, self.remote)
        if not self.experience_level:
            self.experience_level = infer_experience_level(self.title, self.description)
        if not self.country:
            self.country = infer_country(self.location)
        if self.salary_min is not None and self.salary_max is not None and self.salary_max < self.salary_min:
            raise ValueError("Invalid salary range")
        if self.salary_currency:
            self.salary_currency = self.salary_currency.upper()
            if not re.fullmatch(r"[A-Z]{3}", self.salary_currency):
                raise ValueError("Expected a three-letter salary currency")
        return self

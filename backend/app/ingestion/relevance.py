"""Conservative engineering-role selection, independent of employer boilerplate."""

import re

NON_TECH = re.compile(
    r"\b("
    r"recruiter|recruiting|recruitment|talent acquisition|headhunter|"
    r"sales|account executive|business development|bdr|sdr|client success|customer success|sales representative|sales manager|"
    r"marketing|marketer|growth marketer|social media|seo specialist|content marketer|brand manager|"
    r"copywriter|copywriting|content writer|writer|technical writer|communications specialist|"
    r"customer support|customer service|customer care|"
    r"legal|counsel|compliance officer|paralegal|"
    r"finance|accountant|accounting|payroll|bookkeeper|"
    r"people operations|human resources|hr generalist|hr manager|office manager|executive assistant|administrative assistant|"
    r"graphic designer|art director|video editor|animator"
    r")\b",
    re.I,
)

TECH_TITLE = re.compile(
    r"\b(software|sde|swe|backend|frontend|front.?end|back.?end|full.?stack|fullstack|"
    r"machine learning|deep learning|artificial intelligence|generative ai|genai|llm|nlp|"
    r"computer vision|mlops|devops|sre|site reliability|site reliability engineer|data engineer|data scientist|research engineer|"
    r"research scientist|applied scientist|security engineer|cloud engineer|platform engineer|"
    r"infrastructure engineer|ai engineer|ml engineer|firmware engineer|embedded engineer|"
    r"qa engineer|test engineer|systems engineer)\b",
    re.I,
)

TECH_EVIDENCE = re.compile(
    r"\b(python|java|typescript|javascript|c\+\+|pytorch|tensorflow|kubernetes|"
    r"distributed systems|llm|machine learning|sql|golang|rust|docker|linux|react|aws|gcp)\b",
    re.I,
)

PROGRAM_PREFIXES = re.compile(
    r"^(?:\[(?P<bracket_badge>[^\]]+)\]\s*|"
    r"\((?P<paren_badge>[^)]+)\)\s*|"
    r"(?P<prefix_badge>Year at Palantir|"
    r"Palantir Path|"
    r"\d{4}\s+(?:Summer|Fall|Winter|Spring)?\s*(?:Internship|Fellowship|Graduate Program|Grad Program)|"
    r"(?:Summer|Fall|Winter|Spring)\s+\d{4}\s*(?:Internship|Fellowship|Graduate Program|Grad Program)|"
    r"Summer Internship|Winter Internship|Fall Internship|Spring Internship|"
    r"New Grad(?:uate)? Program|"
    r"Early Career Program|"
    r"Rotational Development Program|"
    r"Apprenticeship Program)\s*[-–—:]\s*)",
    re.I,
)


def clean_title_and_badge(title: str) -> tuple[str, str | None]:
    """Strip program prefixes into a badge while retaining the core functional title."""
    s = title.strip()
    match = PROGRAM_PREFIXES.match(s)
    if match:
        badge = (
            match.group("bracket_badge")
            or match.group("paren_badge")
            or match.group("prefix_badge")
            or ""
        ).strip()
        cleaned_title = s[match.end():].strip()
        return cleaned_title, badge if badge else None
    return s, None


def is_cse_role(title: str, description: str = "") -> bool:
    cleaned_title, _ = clean_title_and_badge(title)
    if NON_TECH.search(cleaned_title) or NON_TECH.search(title):
        return False
    if TECH_TITLE.search(cleaned_title) or TECH_TITLE.search(title):
        return True
    return bool(
        re.search(r"\b(engineer|developer|scientist|architect)\b", cleaned_title, re.I)
        and len(set(TECH_EVIDENCE.findall((description or "").lower()))) >= 2
    )

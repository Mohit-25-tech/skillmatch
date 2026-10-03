"""Export the full deliverable tree and text sources into one reviewable Markdown file."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "test-results",
    "playwright-report",
    "artifacts",
    "docs-assets",
}
TARGET = ROOT / "docs" / "SOURCE_CODE.md"
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".db", ".pyc", ".woff", ".woff2"}
files = sorted(
    p
    for p in ROOT.rglob("*")
    if p.is_file()
    and not (set(p.relative_to(ROOT).parts) & EXCLUDED)
    and p.name != ".env"
    and p != TARGET
)
lines = [
    "# SkillMatch AI — complete source\n",
    "Generated from the delivered workspace. Files are grouped by folder. Binary screenshots are listed in the tree and delivered separately.\n",
    "## Full folder tree\n",
    "```text\n",
]
for path in files:
    lines.append(path.relative_to(ROOT).as_posix() + "\n")
lines.append("```\n")
for path in files:
    if path.suffix in BINARY_SUFFIXES:
        continue
    language = {
        ".py": "python",
        ".ts": "typescript",
        ".css": "css",
        ".json": "json",
        ".ipynb": "json",
        ".yml": "yaml",
        ".sql": "sql",
        ".html": "html",
        ".md": "markdown",
        ".svg": "xml",
    }.get(path.suffix, "text")
    lines.append(f"\n## {path.relative_to(ROOT).as_posix()}\n\n````{language}\n")
    lines.append(path.read_text(encoding="utf-8-sig") + "\n````\n")
TARGET.write_text("".join(lines), encoding="utf-8")
print(f"Exported {len(files)} files to {TARGET.relative_to(ROOT)}")

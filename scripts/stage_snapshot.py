"""Write complete, reviewable source snapshots at each stage boundary."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("stage")
parser.add_argument("files", nargs="+")
args = parser.parse_args()
paths = sorted(set(args.files))
output = [f"# Stage {args.stage} — complete changed/new source\n\n", "```text\n", *[p + "\n" for p in paths], "```\n"]
for name in paths:
    file = ROOT / name
    output.extend([f"\n## {name}\n\n````\n", file.read_text(encoding="utf-8-sig"), "\n````\n"])
target = ROOT / "docs" / "stages" / f"{args.stage}_SOURCE.md"
target.write_text("".join(output), encoding="utf-8")
print(f"Wrote {target.relative_to(ROOT)} ({len(paths)} files)")

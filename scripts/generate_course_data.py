"""Export reproducible seed CSVs and create the two executable course notebooks."""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.seed_data import SKILLS, generate_jobs


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def notebook(title: str, sections: list[tuple[str, str]], filename: str) -> None:
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                f"# {title}\n",
                "This notebook uses the deterministic, synthetic SkillMatch seed dataset. Company names are illustrative; these are not real vacancies. Run all cells from top to bottom.\n",
            ],
        }
    ]
    for description, code in sections:
        cells.append({"cell_type": "markdown", "metadata": {}, "source": [description]})
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": code.splitlines(keepends=True),
            }
        )
    result = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 4,
    }
    (ROOT / "notebooks" / filename).write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )


def main() -> None:
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "notebooks").mkdir(exist_ok=True)
    jobs = [
        {
            "id": i + 1,
            **j,
            "skills": "|".join(j["skills"]),
            "posted_date": f"2026-09-{i % 28 + 1:02d}",
        }
        for i, j in enumerate(generate_jobs())
    ]
    write_csv(ROOT / "data" / "jobs.csv", jobs)
    write_csv(ROOT / "data" / "skills.csv", SKILLS)
    load = "from pathlib import Path\nimport pandas as pd\nroot = Path.cwd() if (Path.cwd() / 'data').exists() else Path.cwd().parent\njobs = pd.read_csv(root / 'data' / 'jobs.csv')\nskills = pd.read_csv(root / 'data' / 'skills.csv')\njobs.head()"
    notebook(
        "Job market exploration with Pandas",
        [
            (
                "## 1. Load and inspect\nRead 200 jobs and 300 skills and inspect column types.",
                load,
            ),
            (
                "## 2. Inspect quality\nCount missing values and duplicate records before cleaning.",
                "print(jobs.shape, skills.shape)\nprint(jobs.dtypes)\nprint(jobs.isna().sum())\nprint('Duplicate IDs:', jobs.duplicated(subset=['id']).sum())",
            ),
            (
                "## 3. Clean missing values and duplicates\nInject a controlled missing location and duplicate row to demonstrate cleaning. Keep the original seed data intact.",
                "dirty = pd.concat([jobs, jobs.iloc[[0]]], ignore_index=True)\ndirty.loc[1, 'location'] = None\nclean = dirty.drop_duplicates(subset=['id']).copy()\nclean['location'] = clean['location'].fillna('Not specified')\nfor column in ['salary_min', 'salary_max']:\n    clean[column] = pd.to_numeric(clean[column], errors='coerce')\n    clean[column] = clean[column].fillna(clean[column].median())\nclean['posted_date'] = pd.to_datetime(clean['posted_date'])\nassert len(clean) == 200\nassert clean['location'].isna().sum() == 0\nclean.head()",
            ),
            (
                "## 4. Filter and sort\nFind remote roles with minimum salaries of at least $120,000, ordered by salary.",
                "remote = clean.loc[(clean['location'] == 'Remote') & (clean['salary_min'] >= 120000)]\nremote.sort_values(['salary_max', 'title'], ascending=[False, True])[['title', 'company', 'salary_min', 'salary_max']].head(15)",
            ),
            (
                "## 5. Summarize\nGroup opportunities by role and expand skill lists to count demand.",
                "summary = clean.groupby('title').agg(openings=('id', 'count'), average_min_salary=('salary_min', 'mean'), average_max_salary=('salary_max', 'mean')).round(0)\ndisplay(summary.sort_values('average_max_salary', ascending=False))\ndemand = clean.assign(skill=clean['skills'].str.split('|')).explode('skill')['skill'].value_counts()\ndisplay(demand.head(15))\ndisplay(skills.groupby('category').size().rename('skill_count'))",
            ),
            (
                "## Interpretation\nThese counts describe a balanced synthetic teaching dataset. Do not interpret them as evidence of actual hiring demand or salary levels.",
                "print(f'{len(clean)} unique jobs, {len(skills)} catalog skills, {clean.company.nunique()} example companies')",
            ),
        ],
        "01_pandas_analysis.ipynb",
    )
    notebook(
        "Visualizing opportunities with Matplotlib",
        [
            (
                "## 1. Load the same dataset",
                load
                + "\nimport matplotlib.pyplot as plt\nplt.style.use('seaborn-v0_8-darkgrid')\nplt.rcParams.update({'figure.figsize': (10, 5), 'figure.dpi': 110})\npurple = '#8764c5'\ncyan = '#399a93'",
            ),
            (
                "## 2. Bar chart — most requested skills",
                "demand = jobs.assign(skill=jobs.skills.str.split('|')).explode('skill').skill.value_counts().head(10)\nfig, ax = plt.subplots()\ndemand.sort_values().plot.barh(ax=ax, color=purple)\nax.set(title='Most requested skills in the synthetic catalog', xlabel='Number of postings', ylabel='Skill')\nfig.tight_layout()\nplt.show()",
            ),
            (
                "## 3. Scatter plot — salary bands",
                "fig, ax = plt.subplots()\nax.scatter(jobs.salary_min / 1000, jobs.salary_max / 1000, color=cyan, alpha=0.4, s=65)\nax.set(title='Advertised salary bands', xlabel='Minimum annual salary (USD thousands)', ylabel='Maximum annual salary (USD thousands)')\nfig.tight_layout()\nplt.show()",
            ),
            (
                "## 4. Histogram — salary distribution",
                "fig, ax = plt.subplots()\nax.hist((jobs.salary_min + jobs.salary_max) / 2000, bins=10, color=purple, edgecolor='white')\nax.set(title='Distribution of salary midpoints', xlabel='Annual midpoint salary (USD thousands)', ylabel='Number of postings')\nfig.tight_layout()\nplt.show()",
            ),
            (
                "## 5. Line chart — postings over time",
                "timeline = jobs.groupby(pd.to_datetime(jobs.posted_date)).size().sort_index()\nfig, ax = plt.subplots()\nax.plot(timeline.index, timeline.values, color=cyan, marker='o')\nax.set(title='Synthetic postings over September 2026', xlabel='Posting date', ylabel='Number of postings')\nfig.autofmt_xdate()\nfig.tight_layout()\nplt.show()",
            ),
            (
                "## 6. Pie chart — employment types",
                "counts = jobs.employment_type.value_counts()\nfig, ax = plt.subplots(figsize=(7, 6))\nax.pie(counts.values, labels=counts.index, autopct='%1.1f%%', colors=[purple, cyan], startangle=90, wedgeprops={'edgecolor': 'white'})\nax.set_title('Employment types in the synthetic catalog')\nfig.tight_layout()\nplt.show()",
            ),
            (
                "## What the charts tell us\nThe seed deliberately balances roles and locations. Salary bands are generated with a fixed spread, so the scatter plot is linear by construction. Dates are simulated, not scraped. These plots demonstrate chart selection and labeling, not real market findings.",
                "assert len(jobs) == 200\nprint('Five chart types generated from the shared seed dataset.')",
            ),
        ],
        "02_matplotlib_visualizations.ipynb",
    )
    print("Generated 200 jobs, 300 skills, and two notebooks.")


if __name__ == "__main__":
    main()

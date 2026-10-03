import { Chart, registerables } from "chart.js";
import type { Analytics, Match } from "./types";
Chart.register(...registerables);
export function mountCharts(
  kind: string,
  data: Analytics,
  match: Match | undefined,
  reduced: boolean,
): () => void {
  const charts: Chart[] = [];
  Chart.defaults.color = "#a396b1";
  Chart.defaults.font.family = "DM Sans";
  Chart.defaults.font.size = 11;
  Chart.defaults.borderColor = "#372b4222";
  const base = {
    responsive: true,
    maintainAspectRatio: false,
    animation: reduced ? (false as const) : { duration: 900 },
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false }, ticks: { color: "#aa9ab5" } },
      y: {
        beginAtZero: true,
        grid: { color: "#3e304333" },
        ticks: { precision: 0 },
      },
    },
  };
  if (kind === "radar" && match) {
    const canvas = document.getElementById(
      "radar-chart",
    ) as HTMLCanvasElement | null;
    if (canvas) {
      const labels =
        match.job.skills.length >= 3
          ? match.job.skills
          : ["Skill overlap", "Semantic fit", "Overall fit"];
      const values =
        match.job.skills.length >= 3
          ? labels.map((s) => (match.matched.includes(s) ? 100 : 0))
          : [match.keyword_score, match.semantic_score, match.score];
      charts.push(
        new Chart(canvas, {
          type: "radar",
          data: {
            labels,
            datasets: [
              {
                label: "Your coverage",
                data: values,
                backgroundColor: "#b59aff22",
                borderColor: "#b59aff",
                pointBackgroundColor: "#8ce1d4",
                pointRadius: 3,
                borderWidth: 2,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: reduced ? false : { duration: 900 },
            plugins: { legend: { display: false } },
            scales: {
              r: {
                min: 0,
                max: 100,
                ticks: { display: false, stepSize: 25 },
                grid: { color: "#63476a44" },
                angleLines: { color: "#63476a44" },
                pointLabels: { color: "#b9a7c9", font: { size: 10 } },
              },
            },
          },
        }),
      );
    }
  } else {
    const configs = [
      {
        id: "gap-chart",
        type: "bar" as const,
        labels: Object.keys(data.skill_gaps),
        values: Object.values(data.skill_gaps),
        color: "#b59aff",
        label: "Roles missing skill",
      },
      {
        id: "distribution-chart",
        type: "bar" as const,
        labels: ["0–19%", "20–39%", "40–59%", "60–79%", "80–100%"],
        values: data.score_distribution,
        color: "#8bcfc3",
        label: "Matches",
      },
      {
        id: "demand-chart",
        type: "bar" as const,
        labels: Object.keys(data.in_demand),
        values: Object.values(data.in_demand),
        color: "#99aedb",
        label: "Active roles",
      },
      {
        id: "activity-chart",
        type: "line" as const,
        labels: Object.keys(data.applications_over_time),
        values: Object.values(data.applications_over_time),
        color: "#c29eed",
        label: "Applications",
      },
    ];
    configs.forEach((c) => {
      const canvas = document.getElementById(c.id) as HTMLCanvasElement | null;
      if (canvas)
        charts.push(
          new Chart(canvas, {
            type: c.type,
            data: {
              labels: c.labels,
              datasets: [
                {
                  label: c.label,
                  data: c.values,
                  backgroundColor: c.type === "line" ? "#b59aff12" : c.color,
                  borderColor: c.color,
                  borderWidth: c.type === "line" ? 2 : 0,
                  borderRadius: c.type === "bar" ? 5 : undefined,
                  tension: 0.35,
                  fill: c.type === "line",
                  pointRadius: 4,
                },
              ],
            },
            options: base,
          }),
        );
    });
  }
  return () => charts.forEach((c) => c.destroy());
}

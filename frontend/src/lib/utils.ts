export function escapeHtml(value: unknown): string {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ]!,
  );
}
export function salary(
  min: number | null,
  max: number | null,
  currency?: string | null,
  interval?: string | null,
): string {
  if (min == null && max == null) return "Not disclosed";
  const format = (n: number) =>
    currency
      ? new Intl.NumberFormat(undefined, {
          style: "currency",
          currency,
          maximumFractionDigits: 0,
        }).format(n)
      : n.toLocaleString();
  return `${min == null ? "Up to " : format(min)}${max != null && min != null ? " \u2013 " : ""}${max == null ? "+" : format(max)}${currency ? "" : " (currency not supplied)"}${interval ? " / " + interval : ""}`;
}
export function safeUrl(value: string | null | undefined): string {
  try {
    const url = new URL(value || "");
    return ["http:", "https:"].includes(url.protocol) &&
      !url.username &&
      !url.password
      ? url.href
      : "";
  } catch {
    return "";
  }
}
export function postedAge(value?: string | null): string {
  if (!value) return "Posting date not supplied";
  const minutes = Math.floor((Date.now() - new Date(/Z$|[+-]\d{2}:\d{2}$/.test(value) ? value : value + "Z").getTime()) / 60000);
  if (!Number.isFinite(minutes) || minutes < 0)
    return "Posting date not supplied";
  if (minutes < 1) return "Just posted";
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}
export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}
export function validateFile(file: Pick<File, "name" | "size">): string | null {
  if (!/\.(pdf|docx)$/i.test(file.name))
    return "Please choose a PDF or DOCX file.";
  if (file.size === 0 || file.size > 5 * 1024 * 1024)
    return "Your resume must be between 1 byte and 5 MB.";
  return null;
}
export function scoreLabel(score: number): string {
  return score >= 85
    ? "Excellent match"
    : score >= 65
      ? "Strong match"
      : "Room to grow";
}

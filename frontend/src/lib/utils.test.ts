import { describe, expect, it } from "vitest";
import {
  escapeHtml,
  initials,
  salary,
  scoreLabel,
  validateFile,
  safeUrl,
  postedAge,
} from "./utils";
describe("safe display and resume validation", () => {
  it("escapes untrusted markup and attributes", () =>
    expect(escapeHtml("<img src=\"x\" onerror='x'>&")).toBe(
      "&lt;img src=&quot;x&quot; onerror=&#39;x&#39;&gt;&amp;",
    ));
  it("rejects unsupported and oversized uploads", () => {
    expect(validateFile({ name: "cv.exe", size: 100 })).toBeTruthy();
    expect(
      validateFile({ name: "cv.pdf", size: 6 * 1024 * 1024 }),
    ).toBeTruthy();
    expect(validateFile({ name: "cv.DOCX", size: 1024 })).toBeNull();
  });
  it("formats salaries and names", () => {
    expect(salary(null, null)).toBe("Not disclosed");
    expect(salary(120000, 160000, "USD", "year")).toContain(new Intl.NumberFormat(undefined,{style:"currency",currency:"USD",maximumFractionDigits:0}).format(120000));
    expect(salary(120000, null)).toContain("currency not supplied");
    expect(safeUrl("javascript:alert(1)")).toBe("");
    expect(safeUrl("https://example.org/job")).toBe("https://example.org/job");
    expect(postedAge(null)).toBe("Posting date not supplied");
    expect(initials(" Alex  Morgan ")).toBe("AM");
  });
  it("labels match scores consistently", () => {
    expect(scoreLabel(90)).toBe("Excellent match");
    expect(scoreLabel(70)).toBe("Strong match");
    expect(scoreLabel(40)).toBe("Room to grow");
  });
});

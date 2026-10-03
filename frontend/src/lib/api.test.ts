import { beforeEach, describe, expect, it, vi } from "vitest";
const mock = vi.hoisted(() => ({ ajax: vi.fn() }));
vi.mock("jquery", () => ({ default: { ajax: mock.ajax } }));
import { api, refreshSession, setToken, notificationStream } from "./api";
function response(data: unknown, fail = false) {
  mock.ajax.mockImplementationOnce(() => {
    const chain = {
      done(callback: (value: unknown) => void) {
        if (!fail) queueMicrotask(() => callback(data));
        return chain;
      },
      fail(callback: (value: unknown) => void) {
        if (fail) queueMicrotask(() => callback(data));
        return chain;
      },
    };
    return chain;
  });
}
describe("typed AJAX client", () => {
  beforeEach(() => {
    mock.ajax.mockReset();
    setToken("");
  });
  it("serializes JSON and attaches bearer credentials", async () => {
    setToken("test-token");
    response({ id: 1 });
    expect(await api("/jobs", "POST", { title: "Engineer" })).toEqual({
      id: 1,
    });
    expect(mock.ajax).toHaveBeenCalledWith(
      expect.objectContaining({
        url: "/api/v1/jobs",
        method: "POST",
        data: '{"title":"Engineer"}',
        headers: { Authorization: "Bearer test-token" },
      }),
    );
  });
  it("sends multipart without JSON conversion", async () => {
    const data = new FormData();
    data.append("file", new Blob(["test"]), "cv.docx");
    response({ id: 2 });
    await api("/resumes", "POST", data);
    expect(mock.ajax).toHaveBeenCalledWith(
      expect.objectContaining({ data, contentType: false, processData: false }),
    );
  });
  it("refreshes expired access and retries exactly once", async () => {
    response({ status: 401 }, true);
    response({ access_token: "renewed", user: { id: 7 } });
    response({ items: [] });
    expect(await api("/jobs")).toEqual({ items: [] });
    expect(mock.ajax).toHaveBeenCalledTimes(3);
  });
  it("deduplicates concurrent refresh calls", async () => {
    response({ access_token: "renewed", user: { id: 7 } });
    await Promise.all([refreshSession(), refreshSession()]);
    expect(mock.ajax).toHaveBeenCalledTimes(1);
  });
  it("returns server validation errors without an HTML response", async () => {
    response(
      { status: 422, responseJSON: { detail: [{ msg: "Invalid filter" }] } },
      true,
    );
    await expect(api("/jobs")).rejects.toThrow("Invalid filter");
  });
  it("reports network errors", async () => {
    response({ status: 0 }, true);
    await expect(api("/jobs")).rejects.toThrow("Unable to reach");
  });
  it("parses split SSE frames and cancels the subscription", async () => {
    setToken("stream-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        new ReadableStream({
          start(controller) {
            controller.enqueue(
              new TextEncoder().encode(
                'event: notifications\ndata: {"items":[],"unread":',
              ),
            );
            controller.enqueue(
              new TextEncoder().encode('2,"next_cursor":4}\n\n'),
            );
            controller.close();
          },
        }),
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const data = vi.fn();
    const cancel = notificationStream(data, vi.fn());
    await vi.waitFor(() =>
      expect(data).toHaveBeenCalledWith({
        items: [],
        unread: 2,
        next_cursor: 4,
      }),
    );
    cancel();
    expect(fetchMock.mock.calls[0][0]).not.toContain("token");
    vi.unstubAllGlobals();
  });
});

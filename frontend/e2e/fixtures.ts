import { test as base, type Page, type Request, type Route } from "@playwright/test";

const API = "http://localhost:8000";
const ORIGIN = "http://localhost:3100";

// The app fetches the API cross-origin with credentials, so mocked answers need CORS headers.
const CORS = {
  "access-control-allow-origin": ORIGIN,
  "access-control-allow-credentials": "true",
  "access-control-allow-headers": "content-type",
  "access-control-allow-methods": "GET,POST,PUT,PATCH,OPTIONS",
};

/** A fixed body, or a function of the request (to change state or inspect what was sent). */
type Body = unknown;

function reply(status: number, body?: Body) {
  return (route: Route) => {
    const req = route.request();
    if (req.method() === "OPTIONS") return route.fulfill({ status: 204, headers: CORS });
    const json = typeof body === "function" ? (body as (r: Request) => unknown)(req) : body;
    return route.fulfill({ status, headers: CORS, json: json ?? {} });
  };
}

export type Api = {
  /** Mock one endpoint by path (query ignored, e.g. "/api/v1/portfolio"). Later calls override earlier ones. */
  mock: (path: string, body: Body, status?: number) => Promise<void>;
  /** Give the browser a session cookie (middleware gate) and answer /auth/me with this role. */
  signIn: (role?: "admin" | "user") => Promise<void>;
};

export const test = base.extend<{ api: Api }>({
  // `provide` is Playwright's fixture callback; the conventional name `use` trips react-hooks lint.
  api: async ({ page, context }, provide) => {
    // Hermetic by default: anything not mocked explicitly is a 503, Binance market data is stubbed.
    await page.route(`${API}/**`, (route: Route) =>
      route.request().method() === "OPTIONS"
        ? route.fulfill({ status: 204, headers: CORS })
        : route.fulfill({ status: 503, headers: CORS, body: "unmocked in e2e" }),
    );
    await page.route("https://data-api.binance.vision/**", reply(200, []));
    await page.routeWebSocket(/binance\.vision/, () => {});

    const mock = async (path: string, body: Body, status = 200) => {
      await page.route((url) => url.origin === API && url.pathname === path, reply(status, body));
    };
    await provide({
      mock,
      signIn: async (role = "admin") => {
        await context.addCookies([{ name: "access_token", value: "e2e", domain: "localhost", path: "/" }]);
        await mock("/api/v1/auth/me", { email: "e2e@test.local", role });
      },
    });
  },
});

export { expect } from "@playwright/test";

/** Hold a button long enough for KillSwitch's 1200 ms hold-to-confirm. */
export async function holdFor(page: Page, name: string, ms = 1500) {
  await page.getByRole("button", { name }).hover();
  await page.mouse.down();
  await page.waitForTimeout(ms);
  await page.mouse.up();
}

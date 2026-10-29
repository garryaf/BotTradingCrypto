import { expect, holdFor, test } from "./fixtures";

const LIMITS = {
  max_risk_per_trade_pct: 0.005,
  daily_loss_limit_pct: 2,
  max_drawdown_limit_pct: 8,
  max_spread_pct: 0.08,
  min_24h_volume_usd: 1_000_000,
  max_open_positions: 5,
  data_freshness_max_age_sec: 30,
};

const ALL_GATES_PASS = {
  passed: true,
  rejection_reasons: [],
  expectancy_check: true,
  risk_per_trade_check: true,
  daily_loss_check: true,
  drawdown_check: true,
  spread_check: true,
  stop_loss_check: true,
  balance_lot_check: true,
  max_positions_check: true,
  circuit_breaker_check: true,
  data_freshness_check: true,
  evaluated_at: "2026-10-26T10:00:00Z",
};

test("anonymous visitors are sent to /login", async ({ page, api }) => {
  void api; // installs the hermetic routes
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Masuk ke AUTO-TRADE AA" })).toBeVisible();
});

test("login shows an error on bad credentials and lands on the dashboard on success", async ({ page, api }) => {
  await api.mock("/api/v1/auth/login", { detail: "Invalid email or password" }, 401);
  await page.goto("/login");
  await page.locator('input[type="email"]').fill("e2e@test.local");
  await page.locator('input[type="password"]').fill("wrong-password");
  await page.getByRole("button", { name: "Masuk", exact: true }).click();
  await expect(page.getByText("Email atau password salah.")).toBeVisible();

  await api.mock("/api/v1/auth/login", { email: "e2e@test.local", role: "user" });
  // The real backend sets the session cookie (covered by test_http); signIn() stands in for it
  // so the middleware lets "/" through.
  await api.signIn("user");
  await page.getByRole("button", { name: "Masuk", exact: true }).click();
  await expect(page).toHaveURL("http://localhost:3100/");
  await expect(page.getByText("Equity Portofolio (Paper)")).toBeVisible();
});

test("dashboard renders portfolio and positions, and the empty signal state", async ({ page, api }) => {
  await api.signIn("user");
  await api.mock("/api/v1/portfolio", {
    connected: true,
    equity_usd: 10234.5,
    cash_balance_usd: 8000,
    open_positions_value_usd: 2234.5,
    daily_realized_pnl_usd: 12.3,
    daily_loss_pct: 0,
    current_drawdown_pct: 0,
    high_water_mark_usd: 10234.5,
    history: [
      { time: "2026-10-26T09:00:00Z", equity: 10000 },
      { time: "2026-10-26T10:00:00Z", equity: 10234.5 },
    ],
  });
  await api.mock("/api/v1/positions", [
    {
      id: "p1",
      symbol: "BTCUSDT",
      status: "OPEN",
      quantity: 0.5,
      average_entry_price: 100,
      current_stop_loss: 95,
      take_profit_1: 110,
      take_profit_2: 120,
      is_tp1_hit: false,
      realized_pnl_usd: 0,
      unrealized_pnl_usd: 5,
    },
  ]);
  await api.mock("/api/v1/signals", []);
  await page.goto("/");
  await expect(page.getByText("$8000.00")).toBeVisible();
  await expect(page.getByText("0.500000 @ 100.00")).toBeVisible();
  await expect(page.getByText("Belum ada sinyal.")).toBeVisible();
});

test("kill switch reports a failed stop instead of a false 'engaged', then engages on success", async ({ page, api }) => {
  await api.signIn("admin");
  await api.mock("/api/v1/control/kill", { detail: "boom" }, 500);
  await page.goto("/");

  // Next.js always mounts an empty role=alert route announcer, so match alerts by their text.
  const failure = page.getByRole("alert").filter({ hasText: "EMERGENCY STOP GAGAL" });

  await page.getByRole("button", { name: "EMERGENCY STOP" }).click();
  await holdFor(page, "TAHAN UNTUK KONFIRMASI");
  await expect(failure).toBeVisible();
  await expect(page.getByText("LIVE LOCK ENGAGED")).toHaveCount(0);

  await api.mock("/api/v1/control/kill", { engaged: true, cancelled_signals: 0, elapsed_ms: 3.2 });
  await page.getByRole("button", { name: "EMERGENCY STOP" }).click();
  await holdFor(page, "TAHAN UNTUK KONFIRMASI");
  await expect(page.getByText("LIVE LOCK ENGAGED")).toBeVisible();
  await expect(failure).toHaveCount(0);
});

test("risk panel labels show the thresholds the backend enforces", async ({ page, api }) => {
  await api.signIn("user");
  await api.mock("/api/v1/risk/status", {
    paused: false,
    circuit_breaker_active: false,
    daily_loss_pct: 0,
    current_drawdown_pct: 9,
    limits: { ...LIMITS, max_risk_per_trade_pct: 0.0035, max_open_positions: 3 },
    latest_check: { ...ALL_GATES_PASS, passed: false, drawdown_check: false, rejection_reasons: ["DRAWDOWN_LIMIT_EXCEEDED"] },
  });
  await page.goto("/risk");
  await expect(page.getByText("2. Risk per Trade ≤ 0.35%")).toBeVisible();
  await expect(page.getByText("8. Posisi Terbuka < 3")).toBeVisible();
  await expect(page.getByText("Ditolak: DRAWDOWN_LIMIT_EXCEEDED")).toBeVisible();
});

test("wallet explorer lists scored wallets, and shows an empty state", async ({ page, api }) => {
  await api.signIn("user");
  await api.mock("/api/v1/wallets", [
    {
      address: "WaLLet1111111111111111111111111111111111abcd",
      status: "PENDING_REVIEW",
      composite_score: 82.5,
      win_rate_pct: 66.7,
      profit_factor: 2.1,
      net_pnl_usd: 1234.5,
      last_active_at: null,
    },
  ]);
  await page.goto("/wallets");
  const row = page.getByRole("row", { name: /PENDING_REVIEW/ });
  await expect(row).toContainText("WaLLet…abcd");
  await expect(row).toContainText("82.50");
  await expect(row).toContainText("1234.5000"); // wallet PnL is in SOL (F-29), no "$"
  await expect(row).not.toContainText("$");

  await api.mock("/api/v1/wallets", []);
  await page.reload();
  await expect(page.getByText("Belum ada wallet ter-skor")).toBeVisible();
});

const CANDIDATE = "SynthCand1111111111111111111111111111111wXyz";

function walletRow(status: string) {
  return {
    address: CANDIDATE,
    status,
    composite_score: 82.5,
    win_rate_pct: 66.7,
    profit_factor: 2.1,
    net_pnl_usd: 1234.5,
    last_active_at: null,
  };
}

test("admin approves a scored wallet and the list refreshes; non-admins get no decision buttons", async ({
  page,
  api,
}) => {
  await api.signIn("admin");
  let status = "PENDING_REVIEW";
  let sent: unknown = null;
  await api.mock("/api/v1/wallets", () => [walletRow(status)]);
  await api.mock(`/api/v1/admin/wallets/${CANDIDATE}`, (req: { postDataJSON: () => unknown }) => {
    sent = req.postDataJSON();
    status = "ACTIVE_MONITORED";
    return { address: CANDIDATE, status };
  });
  await page.goto("/wallets");

  const row = page.getByRole("row", { name: /PENDING_REVIEW/ });
  await row.getByRole("button", { name: "Setujui" }).click();
  // Refetched right after the decision, not on the next 10 s poll.
  const approved = page.getByRole("row", { name: /ACTIVE_MONITORED/ });
  await expect(approved).toBeVisible({ timeout: 3000 });
  expect(sent).toEqual({ status: "ACTIVE_MONITORED" });
  await expect(approved.getByRole("button", { name: "Setujui" })).toHaveCount(0);
  await expect(approved.getByRole("button", { name: "Arsipkan" })).toBeVisible();

  await api.signIn("user");
  await page.reload();
  await expect(page.getByRole("row", { name: /ACTIVE_MONITORED/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Arsipkan" })).toHaveCount(0);
  await expect(page.getByLabel("Alamat wallet Solana")).toHaveCount(0);
});

test("admin adds a candidate wallet; a duplicate shows a clear error", async ({ page, api }) => {
  await api.signIn("admin");
  const listed: ReturnType<typeof walletRow>[] = [];
  await api.mock("/api/v1/wallets", () => listed);
  await api.mock("/api/v1/admin/wallets", { detail: "Wallet already registered" }, 409);
  await page.goto("/wallets");

  const input = page.getByLabel("Alamat wallet Solana");
  await input.fill(CANDIDATE);
  await page.getByRole("button", { name: "Tambah kandidat" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "sudah terdaftar" })).toBeVisible();

  await api.mock("/api/v1/admin/wallets", () => {
    listed.push({ ...walletRow("DISCOVERED"), composite_score: 0 });
    return { address: CANDIDATE, status: "DISCOVERED" };
  }, 201);
  await page.getByRole("button", { name: "Tambah kandidat" }).click();
  await expect(page.getByRole("row", { name: /DISCOVERED/ })).toBeVisible({ timeout: 3000 });
  await expect(input).toHaveValue("");
  await expect(page.getByRole("alert").filter({ hasText: "sudah terdaftar" })).toHaveCount(0);
});

test("settings says when the key status could not be loaded", async ({ page, api }) => {
  await api.signIn("user"); // binance-credentials is left unmocked -> 503
  await page.goto("/settings");
  await expect(page.getByRole("alert").filter({ hasText: "Status key tidak bisa dimuat" })).toBeVisible();
});

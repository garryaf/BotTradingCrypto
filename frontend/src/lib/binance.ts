import type { UTCTimestamp } from "lightweight-charts";

export type Candle = {
  time: UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
};

// Binance's dedicated public market-data domains (separate from api.binance.com /
// stream.binance.com) — not subject to the same ISP-level blocking.
const REST_BASE = "https://data-api.binance.vision/api/v3/klines";
const WS_URL = "wss://data-stream.binance.vision/ws";

export async function fetchKlines(
  symbol: string,
  interval: string,
  limit = 200
): Promise<Candle[]> {
  const url = `${REST_BASE}?symbol=${symbol}&interval=${interval}&limit=${limit}`;
  const res = await fetch(url);
  const list: (string | number)[][] = await res.json();
  return list.map((k) => ({
    time: Math.floor(Number(k[0]) / 1000) as UTCTimestamp,
    open: Number(k[1]),
    high: Number(k[2]),
    low: Number(k[3]),
    close: Number(k[4]),
  }));
}

type Listener = (data: unknown) => void;

/** Single shared WS connection to Binance's public data stream, fanned out by topic. */
class BinanceSocket {
  private ws: WebSocket | null = null;
  private listeners = new Map<string, Set<Listener>>();
  private reconnectDelay = 1000;

  private connect() {
    if (this.ws) return;
    const ws = new WebSocket(WS_URL);
    this.ws = ws;

    ws.onopen = () => {
      this.reconnectDelay = 1000;
      const topics = [...this.listeners.keys()];
      if (topics.length) this.send("SUBSCRIBE", topics);
    };
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      const topic =
        msg.e === "24hrTicker"
          ? `${msg.s.toLowerCase()}@ticker`
          : msg.e === "kline"
          ? `${msg.s.toLowerCase()}@kline_${msg.k.i}`
          : null;
      if (topic) this.listeners.get(topic)?.forEach((cb) => cb(msg));
    };
    ws.onclose = () => {
      this.ws = null;
      // ponytail: fixed backoff ceiling, fine for a single-tab dashboard
      setTimeout(() => this.connect(), this.reconnectDelay);
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 15000);
    };
  }

  private send(method: "SUBSCRIBE" | "UNSUBSCRIBE", params: string[]) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ method, params, id: Date.now() }));
    }
  }

  subscribe(topic: string, cb: Listener) {
    this.connect();
    if (!this.listeners.has(topic)) this.listeners.set(topic, new Set());
    this.listeners.get(topic)!.add(cb);
    this.send("SUBSCRIBE", [topic]);

    return () => {
      const set = this.listeners.get(topic);
      set?.delete(cb);
      if (!set?.size) {
        this.listeners.delete(topic);
        this.send("UNSUBSCRIBE", [topic]);
      }
    };
  }
}

export const binanceSocket = new BinanceSocket();

export type TickerData = {
  lastPrice: number;
  pct24h: number;
};

export function subscribeTicker(
  symbol: string,
  cb: (data: TickerData) => void
) {
  return binanceSocket.subscribe(`${symbol.toLowerCase()}@ticker`, (raw) => {
    const d = raw as { c?: string; P?: string };
    if (!d.c) return;
    cb({ lastPrice: Number(d.c), pct24h: Number(d.P ?? 0) });
  });
}

export function subscribeKline(
  symbol: string,
  interval: string,
  cb: (candle: Candle) => void
) {
  return binanceSocket.subscribe(
    `${symbol.toLowerCase()}@kline_${interval}`,
    (raw) => {
      const k = (
        raw as { k?: { t: number; o: string; h: string; l: string; c: string } }
      ).k;
      if (!k) return;
      cb({
        time: Math.floor(Number(k.t) / 1000) as UTCTimestamp,
        open: Number(k.o),
        high: Number(k.h),
        low: Number(k.l),
        close: Number(k.c),
      });
    }
  );
}

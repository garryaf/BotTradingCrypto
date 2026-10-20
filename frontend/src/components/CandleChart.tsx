"use client";

import { useEffect, useRef, useState } from "react";
import {
  createChart,
  CandlestickSeries,
  ColorType,
  type IChartApi,
  type ISeriesApi,
} from "lightweight-charts";
import { fetchKlines, subscribeKline } from "@/lib/binance";

export const INTERVALS: { label: string; value: string }[] = [
  { label: "15m", value: "15m" },
  { label: "1H", value: "1h" },
  { label: "4H", value: "4h" },
  { label: "1D", value: "1d" },
];

export function CandleChart({ symbol, interval }: { symbol: string; interval: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#7b828f",
        fontFamily: "var(--font-geist-mono)",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      timeScale: { borderColor: "rgba(255,255,255,0.08)", timeVisible: true },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.08)" },
      crosshair: {
        vertLine: { color: "rgba(91,140,255,0.4)", labelBackgroundColor: "#11141b" },
        horzLine: { color: "rgba(91,140,255,0.4)", labelBackgroundColor: "#11141b" },
      },
      autoSize: true,
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#3ddc84",
      downColor: "#ff5c5c",
      borderVisible: false,
      wickUpColor: "#3ddc84",
      wickDownColor: "#ff5c5c",
    });
    chartRef.current = chart;
    seriesRef.current = series;

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    fetchKlines(symbol, interval)
      .then((candles) => {
        if (cancelled || !seriesRef.current) return;
        seriesRef.current.setData(candles);
        chartRef.current?.timeScale().fitContent();
      })
      .catch(() => {
        if (!cancelled) setError("Data Binance tidak dapat dimuat (jaringan/ISP).");
      });
    const unsubscribe = subscribeKline(symbol, interval, (candle) => {
      seriesRef.current?.update(candle);
    });
    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [symbol, interval]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      {error && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <p className="rounded-lg border border-warn/30 bg-bg-panel-raised px-3 py-2 text-xs text-warn">
            {error}
          </p>
        </div>
      )}
    </div>
  );
}

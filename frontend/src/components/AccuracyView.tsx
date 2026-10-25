import { useEffect, useMemo, useState } from "react";
import { fetchJson } from "../api";
import type { AccuracyRow, DecisionRow, Summary } from "../types";
import { MetricCard } from "./MetricCard";
import { Button } from "./ui/Button";
import { Download, SlidersHorizontal } from "lucide-react";

function downloadCsv(rows: AccuracyRow[]) {
  const csv = [
    [
      "Delivery UTC",
      "Forecast MW",
      "Actual MW",
      "Error MW",
      "Absolute error MW",
      "Forecast horizon hours",
    ],
    ...rows.map((row) => [
      row.deliveryTime,
      row.forecastMW,
      row.actualMW,
      row.errorMW,
      row.absoluteErrorMW,
      row.forecastHorizonHours ?? "",
    ]),
  ]
    .map((row) => row.join(","))
    .join("\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  link.download = "wind-forecast-accuracy-january-2026.csv";
  link.click();
  URL.revokeObjectURL(link.href);
}

export function AccuracyView() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [rows, setRows] = useState<AccuracyRow[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [maxHorizon, setMaxHorizon] = useState("all");

  useEffect(() => {
    Promise.all([
      fetchJson<Summary>("/api/accuracy/summary"),
      fetchJson<{ data: AccuracyRow[] }>("/api/accuracy/timeseries"),
      fetchJson<{ data: DecisionRow[] }>(
        "/api/decision?from_date=2026-01-01&to_date=2026-01-31",
      ),
    ])
      .then(([nextSummary, timeseries, decisions]) => {
        setSummary(nextSummary);
        const horizons = new Map(
          decisions.data.map((row) => [
            row.deliveryTime,
            row.forecastHorizonHours,
          ]),
        );
        setRows(
          timeseries.data.map((row) => ({
            ...row,
            forecastHorizonHours: horizons.get(row.deliveryTime) ?? null,
          })),
        );
        setState("ready");
      })
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "Unable to load accuracy data",
        );
        setState("error");
      });
  }, []);

  const visibleRows = useMemo(
    () =>
      maxHorizon === "all"
        ? rows
        : rows.filter(
            (row) =>
              row.forecastHorizonHours !== null &&
              row.forecastHorizonHours !== undefined &&
              row.forecastHorizonHours <= Number(maxHorizon),
          ),
    [rows, maxHorizon],
  );
  const breakdownByHour = useMemo(() => {
    const groups = Array.from({ length: 24 }, (_, hour) => ({
      hour,
      total: 0,
      count: 0,
    }));
    visibleRows.forEach((row) => {
      const hour = new Date(row.deliveryTime).getUTCHours();
      groups[hour].total += row.absoluteErrorMW;
      groups[hour].count += 1;
    });
    return groups
      .map((group) => ({
        ...group,
        average: group.count ? group.total / group.count : 0,
      }))
      .filter((group) => group.count);
  }, [visibleRows]);
  const breakdownByHorizon = useMemo(() => {
    const groups = new Map<string, { total: number; count: number }>();
    visibleRows.forEach((row) => {
      if (row.forecastHorizonHours == null) return;
      const bucket = `${Math.floor(row.forecastHorizonHours / 6) * 6}–${Math.floor(row.forecastHorizonHours / 6) * 6 + 6}h`;
      const current = groups.get(bucket) ?? { total: 0, count: 0 };
      current.total += row.absoluteErrorMW;
      current.count += 1;
      groups.set(bucket, current);
    });
    return Array.from(groups.entries())
      .map(([label, value]) => ({ label, average: value.total / value.count }))
      .sort((a, b) =>
        a.label.localeCompare(b.label, undefined, { numeric: true }),
      );
  }, [visibleRows]);
  const visibleP90 = useMemo(() => {
    // The backend summary uses percentile interpolation. Reuse it for the
    // unfiltered view so the card and the banner report the same P90 value.
    if (maxHorizon === "all") return summary?.metrics.absoluteErrorP90MW ?? null;
    const errors = visibleRows
      .map((row) => row.absoluteErrorMW)
      .sort((a, b) => a - b);
    return errors.length
      ? errors[Math.min(errors.length - 1, Math.ceil(errors.length * 0.9) - 1)]
      : null;
  }, [maxHorizon, summary, visibleRows]);

  const chart = useMemo(() => {
    if (!visibleRows.length) return null;
    const width = 900;
    const height = 310;
    const margin = { top: 18, right: 22, bottom: 48, left: 72 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const max = Math.max(
      1,
      ...visibleRows.map((row) => Math.max(row.forecastMW, row.actualMW)),
    );
    const x = (index: number) =>
      margin.left + (index / Math.max(1, visibleRows.length - 1)) * plotWidth;
    const y = (value: number) =>
      margin.top + plotHeight - (value / max) * plotHeight;
    const points = (key: "forecastMW" | "actualMW") =>
      visibleRows.map((row, index) => `${x(index)},${y(row[key])}`).join(" ");
    const xLabels = visibleRows
      .map((row, index) => ({
        index,
        label: new Date(row.deliveryTime).toLocaleDateString("en-GB", {
          day: "2-digit",
          month: "short",
          timeZone: "UTC",
        }),
      }))
      .filter(
        (item, index, labels) =>
          item.index === 0 ||
          item.index === labels.length - 1 ||
          (index > 0 && item.label !== labels[index - 1].label),
      )
      .filter(
        (item, index, labels) =>
          index === 0 || index === labels.length - 1 || index % 7 === 0,
      );
    const yLabels = [0, 0.25, 0.5, 0.75, 1].map((fraction) => ({
      value: Math.round(max * fraction),
      y: margin.top + plotHeight - fraction * plotHeight,
    }));
    return {
      width,
      height,
      margin,
      plotWidth,
      plotHeight,
      max,
      points,
      x,
      y,
      xLabels,
      yLabels,
    };
  }, [visibleRows]);

  const hoveredRow = hoveredIndex === null ? null : visibleRows[hoveredIndex];
  return (
    <section>
      <div className="section-heading mb-2">
        <div>
          <p className="eyebrow">Forecast accuracy</p>
          <h2>How close were the selected forecasts?</h2>
          <p className="section-copy">
            Quantified error for national wind generation across January 2026.
          </p>
        </div>
        <span className="muted">1-31 January 2026 · UTC</span>
      </div>
      {state === "loading" && <p className="notice">Loading metrics…</p>}
      {state === "error" && <p className="notice error">{error}</p>}
      {summary && (
        <>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <SlidersHorizontal size={16} /> Explore the error profile
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <label
                htmlFor="horizon-filter"
                className="text-xs text-slate-500"
              >
                Maximum forecast horizon
              </label>
              <select
                id="horizon-filter"
                value={maxHorizon}
                onChange={(event) => setMaxHorizon(event.target.value)}
                className="rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-800"
              >
                <option value="all">All horizons</option>
                <option value="24">Up to 24 hours</option>
                <option value="36">Up to 36 hours</option>
                <option value="48">Up to 48 hours</option>
              </select>
              <Button
                variant="outline"
                onClick={() => downloadCsv(visibleRows)}
              >
                <Download size={15} /> Export CSV
              </Button>
            </div>
          </div>
          <div className="metric-grid">
            <MetricCard
              label="Average miss"
              value={summary.metrics.maeMW}
              help="The typical size of the forecast miss, ignoring whether wind was over- or under-estimated. Example: 2,142 MW means the forecast was about 2,142 MW away from actual generation on an average hour."
            />
            <MetricCard
              label="Large-miss sensitivity"
              value={summary.metrics.rmseMW}
              help="A miss measure that gives extra weight to large errors. If this is much higher than the average miss, occasional forecast failures are materially affecting risk."
            />
            <MetricCard
              label="Average direction of miss"
              value={summary.metrics.biasMW}
              help="The average forecast minus actual value. A positive result means wind was usually over-forecast; a negative result means it was usually under-forecast. Example: +1,852 MW indicates a typical over-estimate of about 1,852 MW."
            />
            <MetricCard
              label="High-end miss (P90)"
              value={summary.metrics.absoluteErrorP90MW}
              help="A conservative planning guide: 90% of hourly misses were no larger than this amount, while 10% were larger. Example: use it as an indication of the wind volume that may need covering in a difficult hour."
            />
          </div>
          <div className="my-4 rounded-xl border border-orange-100 bg-orange-50 p-4 text-sm leading-6 text-orange-950">
            <strong>What this suggests:</strong> the selected forecasts were{" "}
            {summary.metrics.biasMW !== null && summary.metrics.biasMW > 0
              ? "usually higher than actual wind generation"
              : "usually lower than actual wind generation"}
            . The typical miss was{" "}
            {summary.metrics.maeMW === null
              ? "not available"
              : `${Math.round(summary.metrics.maeMW).toLocaleString()} MW`}
            ; in the filtered view, 90% of misses were at or below{" "}
            {visibleP90 === null
              ? "not available"
              : `${Math.round(visibleP90).toLocaleString()} MW`}
            .
          </div>
          <div className="chart-card">
            <div className="legend">
              <span>
                <i className="legend-forecast" /> Forecast
              </span>
              <span>
                <i className="legend-actual" /> Actual
              </span>
              <span className="legend-hint">
                Hover a point for hourly values
              </span>
            </div>
            {chart && (
              <div className="chart">
                <svg
                  viewBox={`0 0 ${chart.width} ${chart.height}`}
                  role="img"
                  aria-label="Hourly forecast and actual wind generation in megawatts"
                  onMouseLeave={() => setHoveredIndex(null)}
                >
                  <text
                    className="axis-title"
                    transform={`translate(16 ${chart.height / 2}) rotate(-90)`}
                  >
                    Generation (MW)
                  </text>
                  {chart.yLabels.map((tick) => (
                    <g key={tick.value}>
                      <line
                        className="grid-line"
                        x1={chart.margin.left}
                        x2={chart.width - chart.margin.right}
                        y1={tick.y}
                        y2={tick.y}
                      />
                      <text
                        className="axis-label y-label"
                        x={chart.margin.left - 10}
                        y={tick.y + 4}
                      >
                        {tick.value.toLocaleString()}
                      </text>
                    </g>
                  ))}
                  <line
                    className="axis-line"
                    x1={chart.margin.left}
                    x2={chart.margin.left}
                    y1={chart.margin.top}
                    y2={chart.margin.top + chart.plotHeight}
                  />
                  <line
                    className="axis-line"
                    x1={chart.margin.left}
                    x2={chart.width - chart.margin.right}
                    y1={chart.margin.top + chart.plotHeight}
                    y2={chart.margin.top + chart.plotHeight}
                  />
                  <polyline
                    className="forecast-line"
                    points={chart.points("forecastMW")}
                  />
                  <polyline
                    className="actual-line"
                    points={chart.points("actualMW")}
                  />
                  {visibleRows.map((row, index) => (
                    <g
                      key={row.deliveryTime}
                      className="chart-point"
                      onMouseEnter={() => setHoveredIndex(index)}
                    >
                      <circle
                        className="hover-target"
                        cx={chart.x(index)}
                        cy={chart.y(row.forecastMW)}
                        r="5"
                      />
                      <circle
                        className="hover-target"
                        cx={chart.x(index)}
                        cy={chart.y(row.actualMW)}
                        r="5"
                      />
                    </g>
                  ))}
                  {hoveredIndex !== null && (
                    <line
                      className="hover-line"
                      x1={chart.x(hoveredIndex)}
                      x2={chart.x(hoveredIndex)}
                      y1={chart.margin.top}
                      y2={chart.margin.top + chart.plotHeight}
                    />
                  )}
                  {chart.xLabels.map((label) => (
                    <g key={`${label.label}-${label.index}`}>
                      <line
                        className="tick-line"
                        x1={chart.x(label.index)}
                        x2={chart.x(label.index)}
                        y1={chart.margin.top + chart.plotHeight}
                        y2={chart.margin.top + chart.plotHeight + 5}
                      />
                      <text
                        className="axis-label x-label"
                        x={chart.x(label.index)}
                        y={chart.height - 20}
                      >
                        {label.label}
                      </text>
                    </g>
                  ))}
                  <text
                    className="axis-title x-axis-title"
                    x={chart.margin.left + chart.plotWidth / 2}
                    y={chart.height - 2}
                  >
                    Delivery day (UTC)
                  </text>
                </svg>
              </div>
            )}
            {hoveredRow && (
              <div className="chart-tooltip">
                <strong>
                  {new Date(hoveredRow.deliveryTime).toLocaleString([], {
                    dateStyle: "medium",
                    timeStyle: "short",
                  })}
                </strong>
                <span>
                  Forecast:{" "}
                  <b>{Math.round(hoveredRow.forecastMW).toLocaleString()} MW</b>
                </span>
                <span>
                  Actual:{" "}
                  <b>{Math.round(hoveredRow.actualMW).toLocaleString()} MW</b>
                </span>
                <span>
                  Error:{" "}
                  <b>{Math.round(hoveredRow.errorMW).toLocaleString()} MW</b>
                </span>
              </div>
            )}
          </div>
          <p className="assumption-note">
            <strong>744 matched hourly observations.</strong> Error = forecast −
            actual. Actual generation is hourly mean of two half-hour FUELHH
            values.{" "}
          </p>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Average miss by delivery hour
              </h3>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Useful for spotting time-of-day periods where wind forecasts
                need more caution.
              </p>
              <div className="mt-4 space-y-2">
                {breakdownByHour.map((group) => (
                  <div
                    key={group.hour}
                    className="flex items-center gap-2 text-xs"
                  >
                    <span className="w-12 text-slate-500 dark:text-slate-400">
                      {String(group.hour).padStart(2, "0")}:00
                    </span>
                    <div className="h-2 flex-1 rounded-full bg-slate-100 dark:bg-slate-800">
                      <div
                        className="h-2 rounded-full bg-teal-600"
                        style={{
                          width: `${Math.min(100, (group.average / Math.max(1, Math.max(...breakdownByHour.map((item) => item.average)))) * 100)}%`,
                        }}
                      />
                    </div>
                    <span className="w-20 text-right font-medium text-slate-700 dark:text-slate-200">
                      {Math.round(group.average).toLocaleString()} MW
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Average miss by forecast horizon
              </h3>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Compares error for forecasts published at different distances
                from delivery.
              </p>
              <div className="mt-4 space-y-3">
                {breakdownByHorizon.map((group) => (
                  <div
                    key={group.label}
                    className="flex items-center gap-3 text-xs"
                  >
                    <span className="w-16 text-slate-500 dark:text-slate-400">{group.label}</span>
                    <div className="h-3 flex-1 rounded-full bg-slate-100 dark:bg-slate-800">
                      <div
                        className="h-3 rounded-full bg-orange-600"
                        style={{
                          width: `${Math.min(100, (group.average / Math.max(1, Math.max(...breakdownByHorizon.map((item) => item.average)))) * 100)}%`,
                        }}
                      />
                    </div>
                    <span className="w-20 text-right font-medium text-slate-700 dark:text-slate-200">
                      {Math.round(group.average).toLocaleString()} MW
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
}

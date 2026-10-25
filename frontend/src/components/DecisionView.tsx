import { useEffect, useMemo, useState } from "react";
import { fetchJson } from "../api";
import type { AccuracyRow, DecisionRow } from "../types";
import { Tooltip } from "./Tooltip";
import { Button } from "./ui/Button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/Table";
import {
  RefreshCw,
  Download,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
} from "lucide-react";

const MIN_DATE = "2026-01-01";
const MAX_DATE = "2026-01-31";

function formatTime(value: string | null): string {
  return value
    ? new Date(value).toLocaleString([], {
        dateStyle: "short",
        timeStyle: "short",
      })
    : "—";
}
function formatNumber(value: number | null): string {
  return value === null ? "—" : Math.round(value).toLocaleString();
}

function formatPublicationRange(values: string[]): string {
  if (!values.length) return "None";
  if (values[0] === values[values.length - 1]) return formatTime(values[0]);
  return `${formatTime(values[0])} – ${formatTime(values[values.length - 1])}`;
}

function downloadCsv(rows: DecisionRow[]) {
  const csv = [
    [
      "Delivery UTC",
      "Forecast MW",
      "Forecast horizon hours",
      "Publication UTC",
    ],
    ...rows.map((row) => [
      row.deliveryTime,
      row.forecastMW ?? "",
      row.forecastHorizonHours ?? "",
      row.selectedPublishTime ?? "",
    ]),
  ]
    .map((row) => row.join(","))
    .join("\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  link.download = `wind-forecast-${rows[0]?.deliveryTime.slice(0, 10) ?? "data"}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

export function DecisionView() {
  const [day, setDay] = useState(MIN_DATE);
  const [rows, setRows] = useState<DecisionRow[]>([]);
  const [state, setState] = useState<"idle" | "loading" | "ready" | "error">(
    "idle",
  );
  const [error, setError] = useState("");
  const [actuals, setActuals] = useState<Map<string, AccuracyRow>>(new Map());
  const [page, setPage] = useState(0);
  const pageSize = 12;

  async function loadDecision() {
    setState("loading");
    setError("");
    try {
      const [result, accuracy] = await Promise.all([
        fetchJson<{ data: DecisionRow[] }>(
          `/api/decision?from_date=${day}&to_date=${day}`,
        ),
        fetchJson<{ data: AccuracyRow[] }>(
          `/api/accuracy/timeseries?from_date=${day}&to_date=${day}`,
        ),
      ]);
      setRows(result.data);
      setActuals(new Map(accuracy.data.map((row) => [row.deliveryTime, row])));
      setPage(0);
      setState("ready");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load decision data",
      );
      setState("error");
    }
  }

  useEffect(() => {
    void loadDecision();
  }, []);

  const missingCount = rows.filter(
    (row) => row.selectionStatus !== "selected",
  ).length;
  const cutoff = rows[0]?.decisionCutoff ?? null;
  const publicationTimes = rows
    .map((row) => row.selectedPublishTime)
    .filter((value): value is string => Boolean(value))
    .sort();
  const pagedRows = useMemo(
    () => rows.slice(page * pageSize, (page + 1) * pageSize),
    [rows, page],
  );
  const pageCount = Math.max(1, Math.ceil(rows.length / pageSize));
  const horizonValues = rows
    .map((row) => row.forecastHorizonHours)
    .filter((value): value is number => value !== null && value !== undefined);
  const horizonRange = horizonValues.length
    ? `${Math.min(...horizonValues).toFixed(1)}–${Math.max(...horizonValues).toFixed(1)} hours`
    : "—";
  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Day-ahead buying view</p>
          <h2>What forecast was available when buying decisions were made?</h2>
          <p className="section-copy">
            One forecast per delivery hour, selected using the stated decision
            cutoff.
          </p>
        </div>
        <div className="date-control">
          <label htmlFor="delivery-day">
            Delivery date{" "}
            <Tooltip label="data coverage">
              Only 1–31 January 2026 is currently available.
            </Tooltip>
          </label>
          <div className="flex items-center gap-2">
            <input
              id="delivery-day"
              type="date"
              min={MIN_DATE}
              max={MAX_DATE}
              value={day}
              onChange={(event) => setDay(event.target.value)}
            />
            <Button
              onClick={() => void loadDecision()}
              aria-label="Refresh forecast data"
            >
              <RefreshCw size={15} /> <span>Refresh</span>
            </Button>
          </div>
        </div>
      </div>
      <p className="coverage-note">
        Available data: 1-31 January 2026. Dates outside this range are not yet
        supported.
      </p>
      {state === "loading" && (
        <p className="notice">Loading forecast versions…</p>
      )}
      {state === "error" && <p className="notice error">{error}</p>}
      {state === "ready" && rows.length === 0 && (
        <p className="notice">
          No forecast data is available for this date. Choose a date in January
          2026.
        </p>
      )}
      {rows.length > 0 && (
        <>
          <div className="decision-summary">
            <div>
              <span>Decision cutoff</span>
              <strong>{formatTime(cutoff)}</strong>
            </div>
            <div>
              <span>Selected forecast publications</span>
              <strong>{formatPublicationRange(publicationTimes)}</strong>
            </div>
            <div>
              <span>Coverage</span>
              <strong>
                {missingCount
                  ? `${missingCount} hours missing`
                  : `${rows.length} hours covered`}
              </strong>
            </div>
            <div>
              <span>Forecast horizon</span>
              <strong>{horizonRange}</strong>
            </div>
          </div>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-slate-500">
              Use this table to see the forecast that was available before each
              delivery hour.
            </p>
            <Button variant="outline" onClick={() => downloadCsv(rows)}>
              <Download size={15} /> Export CSV
            </Button>
          </div>
          <p className="table-help">
            Forecast horizon is the time between publication and delivery. It
            shows how far ahead each hourly value was known.{" "}
            <Tooltip label="forecast horizon">
              For example, a 16.5-hour horizon means the forecast was published
              16.5 hours before that delivery hour. Longer horizons give you
              more time to act, but they can also carry more uncertainty.
            </Tooltip>
          </p>
          <div className="mt-2 table-wrap">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Delivery (UTC)</TableHead>
                  <TableHead>Forecast (MW)</TableHead>
                  <TableHead>Actual (MW)</TableHead>
                  <TableHead>Error (MW)</TableHead>
                  <TableHead>Forecast horizon</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pagedRows.map((row) => (
                  <TableRow key={row.deliveryTime}>
                    <TableCell className="whitespace-nowrap font-medium text-slate-900 dark:text-slate-100">
                      {formatTime(row.deliveryTime)}
                    </TableCell>
                    <TableCell
                      className={
                        row.forecastMW !== null && row.forecastMW > 20000
                          ? "bg-orange-50 font-semibold text-orange-700 dark:bg-orange-950/40 dark:text-orange-300"
                          : ""
                      }
                    >
                      <span className="inline-flex items-center gap-1.5">
                        {row.forecastMW !== null && row.forecastMW > 20000 && (
                          <AlertTriangle
                            size={14}
                            aria-label="High generation forecast"
                          />
                        )}
                        {formatNumber(row.forecastMW)}
                      </span>
                    </TableCell>
                    <TableCell>
                      {formatNumber(
                        actuals.get(row.deliveryTime)?.actualMW ?? null,
                      )}
                    </TableCell>
                    <TableCell
                      className={
                        (actuals.get(row.deliveryTime)?.absoluteErrorMW ?? 0) >=
                        4000
                          ? "font-semibold text-orange-700"
                          : ""
                      }
                    >
                      {formatNumber(
                        actuals.get(row.deliveryTime)?.errorMW ?? null,
                      )}
                    </TableCell>
                    <TableCell>
                      {row.forecastHorizonHours === null
                        ? "—"
                        : `${row.forecastHorizonHours} h`}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
            <span>
              Showing {page * pageSize + 1}–
              {Math.min((page + 1) * pageSize, rows.length)} of {rows.length}{" "}
              delivery hours
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="px-2 py-1.5"
                disabled={page === 0}
                onClick={() => setPage((value) => Math.max(0, value - 1))}
              >
                <ChevronLeft size={15} /> Previous
              </Button>
              <Button
                variant="outline"
                className="px-2 py-1.5"
                disabled={page >= pageCount - 1}
                onClick={() =>
                  setPage((value) => Math.min(pageCount - 1, value + 1))
                }
              >
                Next <ChevronRight size={15} />
              </Button>
            </div>
          </div>
          <p className="mt-3 flex items-center gap-1.5 text-xs text-slate-500">
            <AlertTriangle size={14} className="text-orange-600" /> Orange
            values are high generation forecasts above 20,000 MW and deserve
            extra attention when planning coverage.
          </p>
        </>
      )}
    </section>
  );
}

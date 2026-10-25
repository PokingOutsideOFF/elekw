import { Tooltip } from "./Tooltip";

export function ScopeBanner() {
  return (
    <aside className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white px-4 py-4 text-slate-900 shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <strong className="block text-sm">National UK wind generation</strong>
        <span className="mt-1 block text-xs text-slate-500 dark:text-slate-400">Elexon BMRS · January 2026 data</span>
      </div>
      <div className="flex items-center gap-1.5 text-left text-xs text-slate-600 dark:text-slate-300 sm:text-right">
        Decision rule: previous-day 09:00 UK cutoff{" "}
        <Tooltip label="decision rule">
          For each delivery hour, we select the latest forecast published at or
          before 09:00 UK time on the previous local calendar day. Later
          revisions are excluded to avoid hindsight bias.
        </Tooltip>
      </div>
    </aside>
  );
}

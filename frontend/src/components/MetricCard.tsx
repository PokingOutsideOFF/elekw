import { Tooltip } from "./Tooltip";
import { Card } from "./ui/Card";

type MetricCardProps = { label: string; value: number | null; help: string };

export function MetricCard({ label, value, help }: MetricCardProps) {
  const formatted = value === null ? "—" : Math.round(value).toLocaleString();
  return (
    <Card className="p-5">
      <div className="flex items-center gap-1.5 text-sm font-semibold text-slate-600 dark:text-slate-300">
        <span>{label}</span>
        <Tooltip label={label}>{help}</Tooltip>
      </div>
      <strong className="mt-3 block text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
        {formatted}{" "}
        <small className="text-sm font-medium text-slate-500 dark:text-slate-400">
          MW
        </small>
      </strong>
    </Card>
  );
}

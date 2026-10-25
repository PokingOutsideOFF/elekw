import type { ReactNode } from "react";
import { Info } from "lucide-react";

type TooltipProps = { label: string; children: ReactNode };

export function Tooltip({ label, children }: TooltipProps) {
  return (
    <span className="group relative inline-flex align-middle">
      <button
        type="button"
        className="grid h-[18px] w-[18px] place-items-center rounded-full border border-slate-400 bg-transparent p-0 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
        aria-label={`More information about ${label}`}
      >
        <Info size={14} />
      </button>
      <span className="invisible absolute bottom-[calc(100%+8px)] right-0 z-10 w-64 rounded-md bg-slate-900 px-3 py-2.5 text-left text-xs leading-5 text-white opacity-0 shadow-lg transition-opacity group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100 dark:bg-slate-700" role="tooltip">
        {children}
      </span>
    </span>
  );
}

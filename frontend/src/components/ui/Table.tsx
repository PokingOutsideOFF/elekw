import type { HTMLAttributes, TableHTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from "react";

export function Table({ className = "", ...props }: TableHTMLAttributes<HTMLTableElement>) {
  return (
    <div className="relative w-full overflow-auto">
      <table className={`w-full caption-bottom text-sm ${className}`} {...props} />
    </div>
  );
}

export function TableHeader({ className = "", ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={`[&_tr]:border-b ${className}`} {...props} />;
}

export function TableBody({ className = "", ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={`[&_tr:last-child]:border-0 ${className}`} {...props} />;
}

export function TableRow({ className = "", ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={`border-b border-slate-200 transition-colors hover:bg-slate-50 data-[state=selected]:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800 dark:data-[state=selected]:bg-slate-800 ${className}`} {...props} />;
}

export function TableHead({ className = "", ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return <th className={`h-11 bg-slate-100 px-4 text-left align-middle text-xs font-semibold text-slate-600 [&:has([role=checkbox])]:pr-0 dark:bg-slate-800 dark:text-slate-300 ${className}`} {...props} />;
}

export function TableCell({ className = "", ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={`p-4 align-middle text-slate-700 [&:has([role=checkbox])]:pr-0 dark:text-slate-300 ${className}`} {...props} />;
}

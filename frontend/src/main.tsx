import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { AccuracyView } from "./components/AccuracyView";
import { DecisionView } from "./components/DecisionView";
import { ScopeBanner } from "./components/ScopeBanner";
import { Badge } from "./components/ui/Badge";
import { Moon, Sun } from "lucide-react";
import "./index.css";

function App() {
  const [view, setView] = useState<"decision" | "accuracy">("decision");
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem("uk-wind-theme");
    return saved
      ? saved === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    localStorage.setItem("uk-wind-theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  return (
    <main className="mx-auto min-h-screen max-w-6xl bg-white px-4 py-6 font-sans text-slate-900 dark:bg-slate-950 dark:text-slate-100 sm:px-7">
      <header className="flex min-h-[52px] items-center justify-between border-b border-slate-200 dark:border-slate-800">
        <a
          className="flex items-center gap-2.5 text-slate-900 no-underline dark:text-slate-100"
          href="/"
          aria-label="UK Wind Forecast home"
        >
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-slate-900 text-sm font-bold text-white dark:bg-slate-100 dark:text-slate-900">
            W
          </span>
          <span>
            <strong className="block text-sm">UK Wind Forecast</strong>
            <small className="mt-0.5 block text-[11px] text-slate-500 dark:text-slate-400">
              Decision support
            </small>
          </span>
        </a>
        <div className="flex items-center gap-3">
          <Badge>January 2026</Badge>
          <span className="hidden text-xs text-slate-500 dark:text-slate-400 sm:inline">
            <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-teal-600" />
            Historical snapshot
          </span>
          <button
            type="button"
            onClick={() => setDarkMode((value) => !value)}
            className="grid h-9 w-9 place-items-center rounded-md border border-slate-300 bg-white text-slate-600 transition-colors hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
            aria-label={
              darkMode ? "Switch to light mode" : "Switch to dark mode"
            }
            title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
          >
            {darkMode ? <Sun size={17} /> : <Moon size={17} />}
          </button>
        </div>
      </header>
      <section className="py-12 sm:py-14">
        <p className="mb-2 text-xs font-bold uppercase tracking-[.14em] text-orange-700 dark:text-orange-400">
          National wind generation
        </p>
        <h1 className="max-w-3xl text-3xl font-semibold leading-none tracking-tight text-slate-900 dark:text-slate-100 sm:text-5xl">
          Forecast decision support
        </h1>
        <p className="mt-5 max-w-xl text-base leading-6 text-slate-600 dark:text-slate-300">
          See the forecast available at the buying cutoff and quantify how much
          it has historically missed by.
        </p>
      </section>
      <ScopeBanner />
      <nav
        className="mt-6 flex gap-1 border-b border-slate-200 dark:border-slate-800"
        aria-label="Views"
      >
        <button
          className={`border-b-2 px-3.5 py-3 text-sm font-semibold transition-colors ${view === "decision" ? "border-slate-900 text-slate-900 dark:border-slate-100 dark:text-slate-100" : "border-transparent text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-900 dark:hover:text-slate-100"}`}
          onClick={() => setView("decision")}
        >
          Day-ahead buying view
        </button>
        <button
          className={`border-b-2 px-3.5 py-3 text-sm font-semibold transition-colors ${view === "accuracy" ? "border-slate-900 text-slate-900 dark:border-slate-100 dark:text-slate-100" : "border-transparent text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-900 dark:hover:text-slate-100"}`}
          onClick={() => setView("accuracy")}
        >
          Forecast accuracy
        </button>
      </nav>
      <div className="min-h-[560px] py-10">
        {view === "decision" ? <DecisionView /> : <AccuracyView />}
      </div>
      <footer className="border-t border-slate-200 pt-4 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
        Source: Elexon BMRS · National wind generation only · Timestamps are
        displayed in your browser timezone; API data is stored in UTC.
      </footer>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);

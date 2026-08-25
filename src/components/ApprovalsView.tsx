import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  CheckSquare,
  ChevronDown,
  CircleX,
  History,
  Scale,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { resolveTask, useTasks } from "../lib/api";
import { formatTime, formatMoney } from "./DashboardView";
import type { ActionTask } from "../lib/types";

const CATEGORY_STYLE: Record<string, string> = {
  Finance: "bg-amber-400/10 text-amber-300 border-amber-400/30",
  Calendar: "bg-indigo-400/10 text-indigo-300 border-indigo-400/30",
  Errands: "bg-emerald-400/10 text-emerald-300 border-emerald-400/30",
  Family: "bg-rose-400/10 text-rose-300 border-rose-400/30",
};

function TaskCard({ task }: { task: ActionTask }) {
  const [open, setOpen] = useState(false);
  const pending = task.status === "pending";
  const resolved = task.status === "approved" || task.status === "rejected";

  const approve = () => {
    resolveTask(task.id, "approved");
    toast.success("Approved and executed", {
      description: `${task.title} was bundled and sent.`,
    });
  };
  const reject = () => {
    resolveTask(task.id, "rejected", "Rejected by user");
    toast.error("Rejected", {
      description: `${task.title} was declined and logged.`,
    });
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
      className={`overflow-hidden rounded-2xl border ${
        resolved
          ? "border-slate-800 bg-slate-900/40"
          : "border-slate-700/60 bg-slate-900/60"
      } shadow-sm`}
    >
      <div className="p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${CATEGORY_STYLE[task.category]}`}
            >
              {task.category}
            </span>
            <span className="text-[11px] text-slate-500">{task.provider}</span>
            {pending && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-400/15 px-2 py-0.5 text-[10px] font-semibold text-amber-300">
                <AlertTriangle className="h-3 w-3" strokeWidth={2} />
                Needs review
              </span>
            )}
          </div>
          {resolved && (
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                task.status === "approved"
                  ? "bg-emerald-400/15 text-emerald-300"
                  : "bg-rose-400/15 text-rose-300"
              }`}
            >
              {task.status === "approved" ? (
                <Check className="h-3 w-3" strokeWidth={2.5} />
              ) : (
                <CircleX className="h-3 w-3" strokeWidth={2.5} />
              )}
              {task.status}
            </span>
          )}
        </div>

        <h3 className="mt-2.5 text-base font-semibold text-slate-100">
          {task.title}
        </h3>
        <p className="mt-1 text-sm leading-relaxed text-slate-400">
          {task.description}
        </p>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          {task.impact > 0 && (
            <span className="inline-flex items-center gap-1.5 rounded-lg bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-200">
              <Scale className="h-3.5 w-3.5 text-amber-300" strokeWidth={1.75} />
              {formatMoney(task.impact, task.currency)}
            </span>
          )}
          {!!task.reason && (
            <span className="inline-flex items-center gap-1.5 rounded-lg bg-rose-400/10 px-2.5 py-1 text-[11px] text-rose-300">
              <AlertTriangle className="h-3.5 w-3.5" strokeWidth={1.75} />
              {task.reason}
            </span>
          )}
          <span className="ml-auto text-[11px] text-slate-500">
            {formatTime(task.timestamp)} · {task.executionMs}ms
          </span>
        </div>

        {pending && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button
              onClick={approve}
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 shadow-sm shadow-emerald-500/25 transition-transform hover:scale-[1.02] active:scale-[0.98]"
            >
              <CheckSquare className="h-4 w-4" strokeWidth={2} />
              Approve & Execute
            </button>
            <button
              onClick={reject}
              className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-sm font-semibold text-rose-300 transition-colors hover:bg-rose-500/20 active:scale-[0.98]"
            >
              <X className="h-4 w-4" strokeWidth={2.25} />
              Reject
            </button>
            <button
              onClick={() => setOpen((o) => !o)}
              className="ml-auto inline-flex items-center gap-1 rounded-lg px-2.5 py-2 text-sm text-slate-400 transition-colors hover:text-slate-200"
            >
              Payload
              <ChevronDown
                className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`}
                strokeWidth={1.75}
              />
            </button>
          </div>
        )}
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-slate-800"
          >
            <div className="overflow-auto bg-slate-950/60 p-4">
              <pre className="font-mono text-xs leading-relaxed text-slate-400">
                {JSON.stringify(task.payload, null, 2)}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {resolved && task.decisionNote && (
        <div className="border-t border-slate-800 bg-slate-950/40 px-5 py-2.5 text-xs text-slate-500">
          Decision note: {task.decisionNote}
        </div>
      )}
    </motion.div>
  );
}

export default function ApprovalsView() {
  const tasks = useTasks();
  const pending = tasks.filter((t) => t.status === "pending");
  const history = tasks
    .filter((t) => t.status === "approved" || t.status === "rejected")
    .sort((a, b) => b.timestamp - a.timestamp);

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <div className="mb-6">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-emerald-400">
          <ArrowRight className="h-3.5 w-3.5" /> Approval Center
        </div>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-100 sm:text-3xl">
          Decisions needing you
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          High-impact agent actions paused for your review. Approve to execute,
          or reject to stop.
        </p>
      </div>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-300">
          Pending ({pending.length})
        </h2>
        {pending.length === 0 ? (
          <div className="grid place-items-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/30 px-6 py-14 text-center">
            <Check className="mb-3 h-8 w-8 text-emerald-400" strokeWidth={1.5} />
            <p className="text-sm font-medium text-slate-200">All caught up</p>
            <p className="mt-1 max-w-sm text-sm text-slate-500">
              LifePilot handled everything within your autonomy thresholds. No
              decisions waiting.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <AnimatePresence>
              {pending.map((t) => (
                <TaskCard key={t.id} task={t} />
              ))}
            </AnimatePresence>
          </div>
        )}
      </section>

      {history.length > 0 && (
        <section className="mt-10">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-300">
            <History className="h-4 w-4" strokeWidth={1.75} />
            Audit history
          </h2>
          <div className="divide-y divide-slate-800 rounded-2xl border border-slate-800 bg-slate-900/40">
            {history.map((t) => (
              <div key={t.id} className="flex items-center gap-3 px-4 py-3">
                {t.status === "approved" ? (
                  <Check className="h-4 w-4 shrink-0 text-emerald-400" strokeWidth={2.5} />
                ) : (
                  <X className="h-4 w-4 shrink-0 text-rose-400" strokeWidth={2.5} />
                )}
                <span className="flex-1 text-sm text-slate-200">{t.title}</span>
                <span className="text-[11px] text-slate-500">{formatTime(t.timestamp)}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
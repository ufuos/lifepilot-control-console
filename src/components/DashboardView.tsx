import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Archive,
  CalendarCheck,
  ChevronDown,
  Cpu,
  Filter,
  Gauge,
  Loader2,
  Search,
  Timer,
  TrendingDown,
  TrendingUp,
  Wallet,
  Zap,
} from "lucide-react";
import { addTask, useLogs, useStats, useTasks } from "../lib/api";
import type { ExecutionLogEntry, TaskCategory } from "../lib/types";

export function formatTime(ts: number) {
  const diff = Date.now() - ts;
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export function formatMoney(value: number, currency?: string) {
  if (value <= 0) return currency ? `0 ${currency}` : "0";
  const v = value % 1 === 0 ? value.toLocaleString() : value.toFixed(2);
  return currency ? `${v} ${currency}` : v;
}

const CATEGORIES: TaskCategory[] = ["Finance", "Calendar", "Errands", "Family"];

const CAT_STYLE: Record<string, string> = {
  Finance: "bg-amber-400/10 text-amber-300 border-amber-400/30",
  Calendar: "bg-indigo-400/10 text-indigo-300 border-indigo-400/30",
  Errands: "bg-emerald-400/10 text-emerald-300 border-emerald-400/30",
  Family: "bg-rose-400/10 text-rose-300 border-rose-400/30",
};

const SEVERITY_DOT: Record<string, string> = {
  auto: "bg-emerald-400",
  escalated: "bg-amber-400",
  resolved: "bg-indigo-400",
};

function MetricCard({
  label,
  value,
  sub,
  trend,
  icon,
  accent,
}: {
  label: string;
  value: string;
  sub: string;
  trend?: "up" | "down";
  icon: React.ReactNode;
  accent: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      className={`relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/50 p-4 shadow-sm`}
    >
      <div className={`absolute inset-x-0 top-0 h-px ${accent}`} />
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400">{label}</span>
        <span className={`grid h-8 w-8 place-items-center rounded-lg ${accent} bg-opacity-10 text-slate-200`}>
          {icon}
        </span>
      </div>
      <div className="mt-3 flex items-end justify-between">
        <div>
          <div className="text-2xl font-semibold tracking-tight text-slate-100">
            {value}
          </div>
          <div className="mt-0.5 text-[11px] text-slate-500">{sub}</div>
        </div>
        {trend && (
          <span
            className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[11px] font-medium ${
              trend === "up"
                ? "bg-emerald-400/15 text-emerald-300"
                : "bg-rose-400/15 text-rose-300"
            }`}
          >
            {trend === "up" ? (
              <TrendingUp className="h-3 w-3" strokeWidth={2} />
            ) : (
              <TrendingDown className="h-3 w-3" strokeWidth={2} />
            )}
            {trend === "up" ? "+12%" : "-3%"}
          </span>
        )}
      </div>
    </motion.div>
  );
}

function LogRow({ log }: { log: ExecutionLogEntry }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 transition-colors hover:border-slate-700">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left"
      >
        <span className={`h-2 w-2 shrink-0 rounded-full ${SEVERITY_DOT[log.severity]}`} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm text-slate-200">{log.title}</span>
          <span className="block text-[11px] text-slate-500">{formatTime(log.timestamp)} · {log.model}</span>
        </span>
        <span className={`rounded-full border px-2 py-0.5 text-[10px] ${CAT_STYLE[log.category]}`}>
          {log.category}
        </span>
        <ChevronDown className={`h-4 w-4 shrink-0 text-slate-500 transition-transform ${open ? "rotate-180" : ""}`} strokeWidth={1.75} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-slate-800"
          >
            <div className="p-3">
              {log.trace.map((step, i) => (
                <div key={i} className="flex items-start gap-2.5 py-1">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400/60" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 text-xs text-slate-200">
                      <span className="font-medium">{step.step}</span>
                      <span className="text-[10px] text-slate-500">{step.model}</span>
                      <span className="ml-auto font-mono text-[10px] text-slate-500">
                        {step.latencyMs}ms
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400">{step.detail}</div>
                  </div>
                </div>
              ))}
              <pre className="mt-2 overflow-auto rounded-lg bg-slate-950/70 p-2 font-mono text-[10px] leading-relaxed text-slate-500">
                {JSON.stringify(log.payload, null, 2)}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function DashboardView({ onGoApprovals }: { onGoApprovals: () => void }) {
  const stats = useStats();
  const tasks = useTasks();
  const logs = useLogs();
  const [search, setSearch] = useState("");
  const [cats, setCats] = useState<TaskCategory[]>([]);

  const pending = tasks.filter((t) => t.status === "pending");

  const filteredLogs = logs.filter(
    (l) =>
      (cats.length === 0 || cats.includes(l.category)) &&
      (search === "" ||
        l.title.toLowerCase().includes(search.toLowerCase()) ||
        l.category.toLowerCase().includes(search.toLowerCase())),
  );

  const toggleCat = (c: TaskCategory) =>
    setCats((prev) =>
      prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c],
    );

  // seed a live action occasionally when dashboard mounts
  const runAuto = () => {
    addTask({
      id: `t-${Date.now()}`,
      title: "Verified home security firmware",
      description: "August lock firmware up to date, no action needed.",
      category: "Errands",
      status: "executed",
      impact: 0,
      requiresApproval: false,
      timestamp: Date.now(),
      executionMs: 31,
      provider: "August Smart Lock",
      payload: { firmware: "3.7.1", status: "ok" },
    });
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      {/* Header */}
      <div className="mb-6">
        <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[11px] font-medium text-emerald-300">
          <Zap className="h-3 w-3" strokeWidth={2} /> Agent running in background
        </div>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-100 sm:text-3xl">
          Control center
        </h1>
        <p className="mt-1 max-w-xl text-sm text-slate-400">
          LifePilot quietly keeps your home in motion - paying bills, calming
          schedules, and running errands. Review what it paused for your say-so.
        </p>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard
          label="Total tasks managed"
          value={`${stats.totalTasks}`}
          sub="this period"
          trend="up"
          icon={<Archive className="h-4 w-4" strokeWidth={1.75} />}
          accent="bg-emerald-400"
        />
        <MetricCard
          label="Time saved"
          value={`${stats.timeSavedHours.toFixed(1)}h`}
          sub="autonomous"
          trend="up"
          icon={<Timer className="h-4 w-4" strokeWidth={1.75} />}
          accent="bg-teal-400"
        />
        <MetricCard
          label="Pending approvals"
          value={`${pending.length}`}
          sub="awaiting you"
          icon={<Gauge className="h-4 w-4" strokeWidth={1.75} />}
          accent="bg-amber-400"
        />
        <MetricCard
          label="Auto-executed"
          value={`${stats.autoExecuted}`}
          sub="within budget"
          trend="down"
          icon={<Cpu className="h-4 w-4" strokeWidth={1.75} />}
          accent="bg-indigo-400"
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Activity feed */}
        <section className="lg:col-span-2">
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
              Activity stream
            </h2>
            <div className="ml-auto flex items-center gap-2">
              <Filter className="h-4 w-4 text-slate-500" strokeWidth={1.75} />
              {CATEGORIES.map((c) => (
                <button
                  key={c}
                  onClick={() => toggleCat(c)}
                  className={`rounded-full border px-2.5 py-1 text-[11px] transition-colors ${
                    cats.includes(c)
                      ? "border-emerald-500/50 bg-emerald-500/15 text-emerald-300"
                      : "border-slate-700 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>
          <div className="relative mb-3">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" strokeWidth={1.75} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search actions or categories..."
              className="w-full rounded-xl border border-slate-800 bg-slate-900/60 py-2 pl-9 pr-3 text-sm text-slate-200 placeholder:text-slate-500 focus:border-emerald-500/50 focus:outline-none"
            />
          </div>

          <div className="space-y-2">
            <LogRow
              log={{
                id: "live",
                taskId: "live",
                title: "LifePilot online",
                category: "Family",
                severity: "auto",
                timestamp: Date.now(),
                latencyMs: 0,
                model: "core",
                trace: [{ step: "Boot", detail: "Agent control loop started", latencyMs: 0 }],
                payload: { status: "ready" },
              }}
            />
            <AnimatePresence>
              {filteredLogs.map((log) => (
                <motion.div key={log.id} layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                  <LogRow log={log} />
                </motion.div>
              ))}
            </AnimatePresence>
            {filteredLogs.length === 0 && (
              <div className="grid place-items-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/30 px-6 py-12 text-center">
                <p className="text-sm text-slate-500">No matching actions.</p>
              </div>
            )}
          </div>
        </section>

        {/* Quick status sidebar */}
        <aside className="space-y-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
            <h3 className="mb-3 text-sm font-semibold text-slate-200">Autonomy status</h3>
            <div className="space-y-3">
              <div>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5 text-slate-400">
                    <Wallet className="h-3.5 w-3.5" strokeWidth={1.75} /> Autonomous budget
                  </span>
                  <span className="font-medium text-slate-200">
                    {formatMoney(stats.budgetUsed, "USD")} / {formatMoney(stats.budgetLimit, "USD")}
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-teal-500"
                    initial={{ width: 0 }}
                    animate={{ width: `${(stats.budgetUsed / stats.budgetLimit) * 100}%` }}
                    transition={{ duration: 0.6 }}
                  />
                </div>
              </div>
              <div>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5 text-slate-400">
                    <CalendarCheck className="h-3.5 w-3.5" strokeWidth={1.75} /> Schedule conflicts
                  </span>
                  <span className="font-medium text-slate-200">{stats.scheduleConflicts}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                  <motion.div
                    className="h-full rounded-full bg-amber-400"
                    initial={{ width: 0 }}
                    animate={{ width: `${(stats.scheduleConflicts / 5) * 100}%` }}
                    transition={{ duration: 0.6 }}
                  />
                </div>
              </div>
            </div>
            <button
              onClick={onGoApprovals}
              className="mt-4 w-full rounded-xl border border-emerald-500/40 bg-emerald-500/10 py-2 text-sm font-medium text-emerald-300 transition-colors hover:bg-emerald-500/20"
            >
              {pending.length > 0
                ? `${pending.length} decision${pending.length > 1 ? "s" : ""} waiting`
                : "View approval center"}
            </button>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
            <h3 className="mb-3 text-sm font-semibold text-slate-200">Agent health</h3>
            <div className="grid grid-cols-3 gap-2 text-center">
              {[
                { label: "Uptime", value: "99.98%" },
                { label: "Latency", value: "212ms" },
                { label: "Queue", value: "0" },
              ].map((h) => (
                <div key={h.label} className="rounded-xl bg-slate-800/60 px-2 py-3">
                  <div className="text-base font-semibold text-emerald-300">{h.value}</div>
                  <div className="mt-0.5 text-[10px] text-slate-500">{h.label}</div>
                </div>
              ))}
            </div>
            <button
              onClick={runAuto}
              className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-xl border border-slate-700 py-2 text-sm text-slate-300 transition-colors hover:border-slate-600 hover:text-slate-100"
            >
              <Loader2 className="h-4 w-4" strokeWidth={1.75} /> Run quick action
            </button>
          </div>
        </aside>
      </div>
    </div>
  );
}
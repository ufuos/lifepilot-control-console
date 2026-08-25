import { motion } from "framer-motion";
import {
  Building2,
  Calendar,
  Home,
  Landmark,
  Mail,
  Plug,
  PlugZap,
  ShoppingBag,
  SlidersHorizontal,
  Unplug,
} from "lucide-react";
import { toast } from "sonner";
import {
  setThreshold,
  toggleIntegration,
  useIntegrations,
  useStats,
} from "../lib/api";
import { formatTime } from "./DashboardView";
import type { IntegrationItem } from "../lib/types";

const ICON_MAP: Record<string, React.ComponentType<{ className?: string; strokeWidth?: number }>> = {
  Calendar,
  Mail,
  Landmark,
  Home,
  Building2,
  ShoppingBag,
};

export default function IntegrationsView() {
  const integrations = useIntegrations();
  const stats = useStats();

  const toggle = (item: IntegrationItem) => {
    toggleIntegration(item.id);
    if (!item.connected) {
      toast.success(`${item.name} connected`, {
        description: `${item.permissions.length} permissions granted.`,
      });
    } else {
      toast(`Disconnected ${item.name}`);
    }
  };

  const setThresholdNow = (v: number) => {
    setThreshold(v);
    toast.success(`Autonomy threshold set to $${v}`, {
      description: "Actions above this require your approval.",
    });
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <div className="mb-6">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-emerald-400">
          <Plug className="h-3.5 w-3.5" /> Connected ecosystem
        </div>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-100 sm:text-3xl">
          Integrations & autonomy
        </h1>
        <p className="mt-1 max-w-xl text-sm text-slate-400">
          Control which providers LifePilot can touch, and how much it can
          spend on its own.
        </p>
      </div>

      {/* Autonomy threshold */}
      <motion.section
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6 rounded-2xl border border-slate-800 bg-slate-900/50 p-5"
      >
        <div className="flex flex-wrap items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-500/15 text-emerald-300">
            <SlidersHorizontal className="h-5 w-5" strokeWidth={1.75} />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-slate-100">Auto-approval threshold</h3>
            <p className="text-xs text-slate-500">
              Payments at or below ${stats.autonomyThreshold} run autonomously.
              Above it, LifePilot waits for you.
            </p>
          </div>
          <div className="rounded-lg bg-slate-950 px-3 py-1.5 font-mono text-lg font-semibold text-emerald-300">
            ${stats.autonomyThreshold}
          </div>
        </div>
        <input
          type="range"
          min={50}
          max={200}
          step={10}
          value={stats.autonomyThreshold}
          onChange={(e) => setThresholdNow(Number(e.target.value))}
          className="mt-4 w-full accent-emerald-400"
        />
        <div className="mt-1 flex justify-between text-[11px] text-slate-500">
          <span>$50 conservative</span>
          <span>$100 balanced</span>
          <span>$200 hands-off</span>
        </div>
      </motion.section>

      {/* Integrations grid */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {integrations.map((item, i) => {
          const Icon = ICON_MAP[item.provider] ?? Plug;
          return (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="grid h-9 w-9 place-items-center rounded-xl bg-slate-800 text-slate-300">
                    <Icon className="h-4 w-4" strokeWidth={1.75} />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-slate-100">{item.name}</h3>
                    <span className="text-[11px] text-slate-500">
                      {item.syncMinutes} min sync · {formatTime(item.lastSync)}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => toggle(item)}
                  className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${
                    item.connected ? "bg-emerald-500" : "bg-slate-700"
                  }`}
                  aria-label={`Toggle ${item.name}`}
                >
                  <span
                    className={`absolute top-0.5 grid h-5 w-5 place-items-center rounded-full bg-white text-slate-900 transition-all ${
                      item.connected ? "left-[22px]" : "left-0.5"
                    }`}
                  >
                    {item.connected ? (
                      <PlugZap className="h-3 w-3" strokeWidth={2.25} />
                    ) : (
                      <Unplug className="h-3 w-3" strokeWidth={2.25} />
                    )}
                  </span>
                </button>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-slate-400">{item.description}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {item.permissions.map((p) => (
                  <span
                    key={p}
                    className={`rounded-full border px-2 py-0.5 font-mono text-[10px] ${
                      item.connected
                        ? "border-emerald-500/30 text-emerald-300"
                        : "border-slate-700 text-slate-500"
                    }`}
                  >
                    {p}
                  </span>
                ))}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
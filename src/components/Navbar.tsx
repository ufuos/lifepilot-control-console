import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  Bot,
  CheckSquare,
  LayoutDashboard,
  LogOut,
  Plug,
  Plus,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import type { View } from "../lib/types";

interface NavbarProps {
  view: View;
  setView: (v: View) => void;
  live: boolean;
  toggleLive: () => void;
  onSimulate: () => void;
  onReset: () => void;
}

const NAV: { key: View; label: string; icon: typeof LayoutDashboard }[] = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "approvals", label: "Approvals", icon: CheckSquare },
  { key: "integrations", label: "Integrations", icon: Plug },
];

export default function Navbar({
  view,
  setView,
  live,
  toggleLive,
  onSimulate,
  onReset,
}: NavbarProps) {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-[#0b0f17]/85 backdrop-blur-lg">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-4 sm:px-6">
        {/* Brand */}
        <div className="flex items-center gap-2.5">
          <div className="relative grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-emerald-400 to-teal-600 shadow-lg shadow-emerald-500/20">
            <Sparkles className="h-5 w-5 text-slate-950" strokeWidth={1.75} />
          </div>
          <div className="hidden sm:block">
            <div className="text-sm font-semibold tracking-tight text-slate-100">
              LifePilot
            </div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">
              Everyday AI Agent
            </div>
          </div>
        </div>

        <span className="hidden rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-medium text-emerald-300 md:inline-flex">
          AWS Strands Hackathon
        </span>

        {/* Nav */}
        <nav className="ml-auto flex items-center gap-1">
          {NAV.map((n) => {
            const active = view === n.key;
            return (
              <button
                key={n.key}
                onClick={() => setView(n.key)}
                className={`relative flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? "text-slate-100"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {active && (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 rounded-lg bg-slate-800/80"
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                )}
                <n.icon className="relative z-10 h-4 w-4" strokeWidth={1.75} />
                <span className="relative z-10 hidden md:inline">{n.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Live beacon */}
        <button
          onClick={toggleLive}
          className="flex items-center gap-1.5 rounded-lg border border-slate-700/80 px-2.5 py-1.5 text-xs font-medium text-slate-300 transition-colors hover:border-slate-600"
          title={live ? "Simulation running" : "Simulation paused"}
        >
          <Bot className="h-3.5 w-3.5 text-indigo-300" strokeWidth={1.75} />
          <span className="relative flex h-2 w-2">
            {live && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            )}
            <span
              className={`relative inline-flex h-2 w-2 rounded-full ${
                live ? "bg-emerald-400" : "bg-slate-600"
              }`}
            />
          </span>
          <span className="hidden sm:inline">
            {live ? "Live" : "Idle"}
          </span>
        </button>

        <div className="hidden h-6 w-px bg-slate-800 sm:block" />

        {/* Actions */}
        <button
          onClick={onSimulate}
          className="hidden items-center gap-1.5 rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-semibold text-slate-950 shadow-sm shadow-emerald-500/30 transition-transform hover:scale-[1.03] active:scale-[0.98] sm:flex"
        >
          <Plus className="h-3.5 w-3.5" strokeWidth={2.25} />
          Simulate
        </button>
        <button
          onClick={onReset}
          className="grid h-8 w-8 place-items-center rounded-lg border border-slate-700/80 text-slate-400 transition-colors hover:text-slate-200"
          title="Reset data"
        >
          <RotateCcw className="h-3.5 w-3.5" strokeWidth={1.75} />
        </button>
      </div>
    </header>
  );
}
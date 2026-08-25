import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Button } from "./components/ui/button";
import { toast } from "sonner";
import Navbar from "./components/Navbar";
import DashboardView from "./components/DashboardView";
import ApprovalsView from "./components/ApprovalsView";
import IntegrationsView from "./components/IntegrationsView";
import { resetData, simulateBackground, useStats } from "./lib/api";
import type { View } from "./lib/types";

function FloatingNotif() {
  const pending = useStats().pendingApprovals;
  return (
    <AnimatePresence>
      {pending > 0 && (
        <motion.div
          initial={{ x: 120, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 120, opacity: 0 }}
          transition={{ type: "spring", stiffness: 260, damping: 22 }}
          className="fixed bottom-5 right-5 z-50"
        >
          <div className="flex items-center gap-3 rounded-xl border border-amber-500/40 bg-slate-900/95 px-4 py-3 shadow-xl shadow-black/40 backdrop-blur">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-amber-400" />
            </span>
            <div>
              <div className="text-sm font-medium text-slate-100">
                {pending} decision{pending > 1 ? "s" : ""} pending
              </div>
              <div className="text-[11px] text-slate-400">
                LifePilot is pausing high-impact actions
              </div>
            </div>
            <Button size="sm" className="ml-2 bg-emerald-500 text-slate-950 hover:bg-emerald-400">
              Review
            </Button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default function App() {
  const [view, setView] = useState<View>("dashboard");
  const [live, setLive] = useState(true);

  // Live background simulation: ~every 7 seconds, spawn an agent action.
  useEffect(() => {
    if (!live) return;
    const id = setInterval(() => {
      simulateBackground(45);
      toast.success("LifePilot took an action", {
        description: "A new background event was logged. Check the activity stream.",
      });
    }, 7000);
    return () => clearInterval(id);
  }, [live]);

  const onSimulate = useCallback(() => {
    simulateBackground(45);
    toast.success("Action simulated", {
      description: "A fresh background agent event was generated.",
    });
  }, []);

  const onReset = useCallback(() => {
    resetData();
    toast.info("Data reset", { description: "Restored the demo dataset." });
  }, []);

  return (
    <div className="min-h-[100dvh] bg-[#0b0f17] text-slate-100 antialiased">
      {/* ambient glow */}
      <div className="pointer-events-none fixed inset-x-0 top-0 -z-0 h-72 bg-gradient-to-b from-emerald-500/[0.07] to-transparent" />

      <Navbar
        view={view}
        setView={setView}
        live={live}
        toggleLive={() => setLive((l) => !l)}
        onSimulate={onSimulate}
        onReset={onReset}
      />

      <main className="relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={view}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
          >
            {view === "dashboard" && (
              <DashboardView onGoApprovals={() => setView("approvals")} />
            )}
            {view === "approvals" && <ApprovalsView />}
            {view === "integrations" && <IntegrationsView />}
          </motion.div>
        </AnimatePresence>
      </main>

      <FloatingNotif />
    </div>
  );
}
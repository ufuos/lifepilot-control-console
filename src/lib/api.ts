import { useEffect, useState } from "react";
import {
  initialIntegrations,
  initialLogs,
  initialStats,
  initialTasks,
} from "./data";
import type {
  ActionTask,
  ExecutionLogEntry,
  IntegrationItem,
  SystemStats,
} from "./types";

const KEYS = {
  tasks: "lifepilot.tasks",
  logs: "lifepilot.logs",
  stats: "lifepilot.stats",
  integrations: "lifepilot.integrations",
};

function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}
function save(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* ignore quota */
  }
}

let tasks: ActionTask[] = [];
let logs: ExecutionLogEntry[] = [];
let stats: SystemStats = { ...initialStats };
let integrations: IntegrationItem[] = [];

function seed() {
  if (tasks.length === 0 && !localStorage.getItem(KEYS.tasks)) {
    tasks = load(KEYS.tasks, initialTasks);
  }
  if (logs.length === 0) logs = load(KEYS.logs, initialLogs);
  if (stats.totalTasks === 0) stats = load(KEYS.stats, initialStats);
  if (integrations.length === 0)
    integrations = load(KEYS.integrations, initialIntegrations);
  persist();
}
seed();

function persist() {
  save(KEYS.tasks, tasks);
  save(KEYS.logs, logs);
  save(KEYS.stats, stats);
  save(KEYS.integrations, integrations);
}

let listeners: Array<() => void> = [];
function notify() {
  persist();
  listeners.forEach((l) => l());
}

// Reactive store hook
export function useStore<T>(selector: () => T): T {
  const [value, setValue] = useState<T>(selector);
  useEffect(() => {
    const handler = () => setValue(selector());
    listeners.push(handler);
    return () => {
      listeners = listeners.filter((l) => l !== handler);
    };
  }, []);
  return value;
}

export const getTasks = () => tasks;
export const getLogs = () => logs;

// --- Mutations ---
export function setTasks(next: ActionTask[]) {
  tasks = next;
  notify();
}

export function addTask(task: ActionTask) {
  tasks = [task, ...tasks];
  logs = [
    {
      id: `log-${Date.now()}`,
      taskId: task.id,
      title: task.title,
      category: task.category,
      severity: task.requiresApproval ? "escalated" : "auto",
      timestamp: Date.now(),
      latencyMs: task.executionMs + 180,
      model: task.requiresApproval ? "claude-sonnet" : "claude-haiku",
      trace: [
        { step: "Classify", detail: `Detected ${task.category.toLowerCase()} action`, latencyMs: 40 },
        { step: "Policy check", detail: task.requiresApproval ? "Escalated for review" : "Auto-eligible", latencyMs: 50 },
        { step: "Execute", detail: task.title, latencyMs: task.executionMs },
      ],
      payload: task.payload,
    },
    ...logs,
  ];
  if (!task.requiresApproval) {
    stats = { ...stats, totalTasks: stats.totalTasks + 1, autoExecuted: stats.autoExecuted + 1 };
  } else {
    stats = { ...stats, totalTasks: stats.totalTasks + 1, pendingApprovals: stats.pendingApprovals + 1 };
  }
  notify();
}

export function resolveTask(id: string, action: "approved" | "rejected", note?: string) {
  const idx = tasks.findIndex((t) => t.id === id);
  if (idx === -1) return;
  const task = tasks[idx];
  tasks[idx] = { ...task, status: action, decisionNote: note };
  logs = [
    {
      id: `log-${Date.now()}`,
      taskId: task.id,
      title: `${action === "approved" ? "Approved" : "Rejected"}: ${task.title}`,
      category: task.category,
      severity: "resolved",
      timestamp: Date.now(),
      latencyMs: 300,
      model: "policy-review",
      trace: [
        { step: "Bundled", detail: `Decision: ${action}`, latencyMs: 120 },
        { step: "Commit", detail: note ?? "no note", latencyMs: 74 },
        { step: "Log", detail: "Audit entry persisted", latencyMs: 40 },
      ],
      payload: { decision: action },
    },
    ...logs,
  ];
  stats = {
    ...stats,
    pendingApprovals: Math.max(0, stats.pendingApprovals - 1),
    timeSavedHours: stats.timeSavedHours + 0.4,
  };
  notify();
}

export function setThreshold(value: number) {
  stats = { ...stats, autonomyThreshold: value };
  notify();
}

export function toggleIntegration(id: string) {
  integrations = integrations.map((i) =>
    i.id === id ? { ...i, connected: !i.connected, lastSync: Date.now() } : i,
  );
  notify();
}

export function setIntegrationSync(id: string, minutes: number) {
  integrations = integrations.map((i) =>
    i.id === id ? { ...i, syncMinutes: minutes, lastSync: Date.now() } : i,
  );
  notify();
}

export function resetData() {
  tasks = initialTasks;
  logs = initialLogs;
  stats = { ...initialStats };
  integrations = initialIntegrations;
  notify();
}

type Template = Omit<
  ActionTask,
  "id" | "status" | "requiresApproval" | "timestamp" | "executionMs"
>;

export function simulateBackground(thresholdPct: number) {
  const autos: Template[] = [
    {
      title: "Paid streaming bundle renewal",
      description: "Recurring Disney+ bundle renewed within budget.",
      category: "Finance",
      impact: 16,
      currency: "USD",
      provider: "Chase Bank",
      payload: { amount: 16, auto: true },
    },
    {
      title: "Synced commute re-route",
      description: "Detected traffic delay, updated morning commute.",
      category: "Calendar",
      impact: 0,
      provider: "Google Maps",
      payload: { reroute: "I-90 via Express Lane" },
    },
    {
      title: "Restocked coffee beans",
      description: "Smart pantry refilled 2 lb house blend order.",
      category: "Errands",
      impact: 24,
      currency: "USD",
      provider: "Instacart",
      payload: { items: 1, qty: "2lb" },
    },
    {
      title: "Checked kids' school insurance claim",
      description: "Pre-approved school trip coverage verified.",
      category: "Family",
      impact: 0,
      provider: "Berkeley Unified",
      payload: { trip: "Science museum" },
    },
  ];
  const escalations: Template[] = [
    {
      title: "Insurance premium increase",
      description: `Policy renewal up $129 (above $${stats.autonomyThreshold} limit). Agent paused for review.`,
      category: "Finance",
      impact: 129,
      currency: "USD",
      provider: "State Farm",
      reason: "Premium variance above auto-approval threshold.",
      payload: { amount: 129, policy: "Home ••• 2201" },
    },
    {
      title: "Dinner reservation conflict",
      description: "Anniversary dinner overlaps late meeting; suggests 8:45 PM slot.",
      category: "Calendar",
      impact: 0,
      provider: "OpenTable",
      reason: "New event conflicts with confirmed reservation.",
      payload: { proposed: "8:45 PM", current: "7:00 PM" },
    },
    {
      title: "Bulk paper goods order variance",
      description: "Monthly bulk order rose 9%. Agent proposes switching brand.",
      category: "Errands",
      impact: 11,
      currency: "USD",
      provider: "Amazon",
      reason: "Recurring purchase price drift detected.",
      payload: { deltaPct: "+9%", alternate: "Kirkland" },
    },
  ];
  const escalated =
    Math.random() * 100 < thresholdPct && escalations.length > 0;
  const chosen = escalated
    ? escalations[Math.floor(Math.random() * escalations.length)]
    : autos[Math.floor(Math.random() * autos.length)];
  addTask({
    id: `t-${Date.now()}`,
    title: chosen.title,
    description: chosen.description,
    category: chosen.category as ActionTask["category"],
    status: escalated ? "pending" : "executed",
    impact: chosen.impact,
    currency: chosen.currency,
    requiresApproval: escalated,
    reason: chosen.reason,
    timestamp: Date.now(),
    executionMs: Math.floor(20 + Math.random() * 60),
    provider: chosen.provider,
    payload: chosen.payload,
  });
}

export function useStats() {
  return useStore(() => stats);
}
export function useTasks() {
  return useStore(() => tasks);
}
export function useLogs() {
  return useStore(() => logs);
}
export function useIntegrations() {
  return useStore(() => integrations);
}

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
  return `${value > 0 ? value : ""}${currency ? ` ${currency}` : ""}`.trim();
}
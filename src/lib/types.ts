export type View = "dashboard" | "approvals" | "integrations";

export type TaskStatus = "pending" | "approved" | "rejected" | "executed";
export type TaskCategory = "Finance" | "Calendar" | "Errands" | "Family";

export interface ActionTask {
  id: string;
  title: string;
  description: string;
  category: TaskCategory;
  status: TaskStatus;
  impact: number;
  currency?: string;
  requiresApproval: boolean;
  reason?: string;
  timestamp: number;
  executionMs: number;
  provider: string;
  payload: Record<string, unknown>;
  decisionNote?: string;
}

export interface SystemStats {
  totalTasks: number;
  timeSavedHours: number;
  pendingApprovals: number;
  activeAutomations: number;
  autoExecuted: number;
  autonomyThreshold: number;
  budgetUsed: number;
  budgetLimit: number;
  scheduleConflicts: number;
}

export interface IntegrationItem {
  id: string;
  name: string;
  provider: string;
  description: string;
  connected: boolean;
  permissions: string[];
  category: TaskCategory;
  syncMinutes: number;
  lastSync: number;
}

export interface AgentHealthMetric {
  label: string;
  value: number;
  unit: string;
}

export interface ExecutionTrace {
  step: string;
  detail: string;
  model?: string;
  latencyMs: number;
}

export interface ExecutionLogEntry {
  id: string;
  taskId: string;
  title: string;
  category: TaskCategory;
  severity: "auto" | "escalated" | "resolved";
  timestamp: number;
  latencyMs: number;
  model: string;
  trace: ExecutionTrace[];
  payload: Record<string, unknown>;
}

export interface FilterState {
  search: string;
  categories: TaskCategory[];
  statuses: TaskStatus[];
}
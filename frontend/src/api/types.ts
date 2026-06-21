export interface Experiment {
  id: string;
  name: string;
  description: string;
}

export interface ExperimentResult {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  log: string[];
  result?: any;
}

export interface MassFaceReadings {
  MASS_FACE: number;
  LOCAL_COMP_LOOP: number;
  LOOP_HOLD_13: number;
  BOUNDARY_LEAK: number;
  DIAG_MINUS_AXIS_LOOP: number;
  timestamp: string;
}

export interface SCFSnapshot {
  core: number;
  bagua_mean: number;
  hex64_mean: number;
  converged: boolean;
  max_change: number;
}

export interface MNQ9Status {
  omega: number;
  B_conf: number;
  kernel: number;
  history_length: number;
}

export interface KernelStatus {
  step_count: number;
  field: number[][];
  fingerprint: string;
  strict_gate: boolean;
  dynamic_gate: boolean;
}

export interface Snapshot {
  id: string;
  timestamp: string;
  experiment: string;
  fingerprint: string;
}

export interface HistoryEntry {
  id: string;
  name: string;
  timestamp: string;
  status: string;
  result?: any;
}

export interface CGDConstraint {
  name: string;
  satisfied: boolean;
  value: number;
  threshold: number;
}

export interface CGDStatus {
  constraints: CGDConstraint[];
  violation_count: number;
  total_constraints: number;
  history: { timestamp: string; violations: number }[];
}

export interface DeepResult {
  text: string;
  syntax_valid: boolean;
  entropy: number;
  kappa_signature: string;
}

export interface KappaSnapshotDetail {
  id: string;
  timestamp: string;
  experiment: string;
  fingerprint: string;
  data: any;
}

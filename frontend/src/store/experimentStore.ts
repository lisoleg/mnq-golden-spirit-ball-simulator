import { create } from 'zustand';
import * as experimentApi from '../api/experiment';
import type { Experiment, ExperimentResult, HistoryEntry } from '../api/types';

interface ExperimentState {
  experiments: Experiment[];
  currentTask: ExperimentResult | null;
  history: HistoryEntry[];
  loading: boolean;
  error: string | null;
  fetchExperiments: () => Promise<void>;
  runExperiment: (id: string, params: Record<string, any>) => Promise<string>;
  updateTaskStatus: (taskId: string) => Promise<void>;
  fetchHistory: () => Promise<void>;
  clearError: () => void;
}

export const useExperimentStore = create<ExperimentState>((set) => ({
  experiments: [],
  currentTask: null,
  history: [],
  loading: false,
  error: null,

  fetchExperiments: async () => {
    set({ loading: true, error: null });
    try {
      const experiments = await experimentApi.fetchExperiments();
      set({ experiments, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  runExperiment: async (id, params) => {
    set({ loading: true, error: null });
    try {
      const { task_id } = await experimentApi.runExperiment(id, params);
      set({
        currentTask: {
          task_id,
          status: 'pending',
          progress: 0,
          log: [],
        },
        loading: false,
      });
      return task_id;
    } catch (e: any) {
      set({ error: e.message, loading: false });
      throw e;
    }
  },

  updateTaskStatus: async (taskId) => {
    try {
      const result = await experimentApi.fetchExperimentStatus(taskId);
      set({ currentTask: result });
    } catch (e: any) {
      console.error('Failed to update task status:', e);
    }
  },

  fetchHistory: async () => {
    set({ loading: true, error: null });
    try {
      const history = await experimentApi.fetchHistory();
      set({ history, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  clearError: () => set({ error: null }),
}));

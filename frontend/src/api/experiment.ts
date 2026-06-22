import api from './client';
import type { Experiment, ExperimentResult, HistoryEntry } from './types';

export const fetchExperiments = async (): Promise<Experiment[]> => {
  const res = await api.get('/experiment/list');
  // Backend returns { experiments: [...] }
  return res.data.experiments ?? res.data;
};

export const runExperiment = async (
  id: string,
  params: Record<string, any>,
): Promise<{ task_id: string }> => {
  const res = await api.post('/experiment/run', { experiment_id: id, params });
  return res.data;
};

export const fetchExperimentStatus = async (
  taskId: string,
): Promise<ExperimentResult> => {
  const res = await api.get(`/experiment/status/${taskId}`);
  return res.data;
};

export const fetchHistory = async (): Promise<HistoryEntry[]> => {
  const res = await api.get('/experiment/history');
  // Backend returns { history: [...] }
  return res.data.history ?? res.data;
};

export const fetchHistoryDetail = async (
  id: string,
): Promise<HistoryEntry> => {
  const res = await api.get(`/experiment/history/${id}`);
  return res.data;
};

import api from './client';
import type { Snapshot, KappaSnapshotDetail } from './types';

export const fetchSnapshots = async (): Promise<Snapshot[]> => {
  const res = await api.get('/kappa/list');
  return res.data.snapshots ?? res.data;
};

export const fetchSnapshotDetail = async (
  id: string,
): Promise<KappaSnapshotDetail> => {
  const res = await api.get(`/kappa/${id}`);
  return res.data.snapshot ?? res.data;
};

export const deleteSnapshot = async (id: string): Promise<void> => {
  await api.delete(`/kappa/${id}`);
};

export const createSnapshot = async (
  experiment: string,
): Promise<Snapshot> => {
  const res = await api.post('/kappa/export', { experiment_id: experiment });
  return res.data;
};

export const downloadSnapshot = async (id: string): Promise<any> => {
  const res = await api.get(`/kappa/${id}/download`);
  return res.data;
};

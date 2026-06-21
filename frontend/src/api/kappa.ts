import api from './client';
import type { Snapshot, KappaSnapshotDetail } from './types';

export const fetchSnapshots = async (): Promise<Snapshot[]> => {
  const res = await api.get('/kappa/snapshots');
  return res.data;
};

export const fetchSnapshotDetail = async (
  id: string,
): Promise<KappaSnapshotDetail> => {
  const res = await api.get(`/kappa/snapshots/${id}`);
  return res.data;
};

export const deleteSnapshot = async (id: string): Promise<void> => {
  await api.delete(`/kappa/snapshots/${id}`);
};

export const createSnapshot = async (
  experiment: string,
): Promise<Snapshot> => {
  const res = await api.post('/kappa/snapshots', { experiment });
  return res.data;
};

export const downloadSnapshot = async (id: string): Promise<any> => {
  const res = await api.get(`/kappa/snapshots/${id}/download`);
  return res.data;
};

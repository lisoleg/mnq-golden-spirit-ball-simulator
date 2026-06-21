import api from './client';
import type { SCFSnapshot } from './types';

export const fetchSCFStatus = async (): Promise<SCFSnapshot> => {
  const res = await api.get('/scf/status');
  return res.data;
};

export const scfStep = async (): Promise<SCFSnapshot> => {
  const res = await api.post('/scf/step');
  return res.data;
};

export const scfRunToConvergence = async (): Promise<SCFSnapshot[]> => {
  const res = await api.post('/scf/run_to_convergence');
  return res.data;
};

export const fetchSCFHistory = async (
  limit: number = 100,
): Promise<SCFSnapshot[]> => {
  const res = await api.get(`/scf/history?limit=${limit}`);
  return res.data;
};

import api from './client';
import type { CGDStatus } from './types';

export const fetchCGDStatus = async (): Promise<CGDStatus> => {
  const res = await api.get('/cgd/status');
  return res.data;
};

export const cgdStep = async (): Promise<CGDStatus> => {
  const res = await api.post('/cgd/step');
  return res.data;
};

export const fetchCGDHistory = async (
  limit: number = 100,
): Promise<{ timestamp: string; violations: number }[]> => {
  const res = await api.get(`/cgd/history?limit=${limit}`);
  return res.data;
};

import api from './client';
import type { CGDStatus } from './types';

export const fetchCGDStatus = async (): Promise<CGDStatus> => {
  const res = await api.get('/cgd/status');
  return res.data;
};

export const cgdStep = async (): Promise<any> => {
  // Backend has no /step endpoint; use /violation for state update
  const res = await api.get('/cgd/violation');
  return res.data;
};

export const fetchCGDHistory = async (
  limit: number = 100,
): Promise<{ timestamp: string; violations: number }[]> => {
  // Backend has no /history endpoint; return empty array gracefully
  return [];
};

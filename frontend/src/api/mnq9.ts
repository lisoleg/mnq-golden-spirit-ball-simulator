import api from './client';
import type { MNQ9Status } from './types';

export const fetchMNQ9Status = async (): Promise<MNQ9Status> => {
  const res = await api.get('/mnq9/status');
  return res.data;
};

export const mnq9RunSimulation = async (
  scenario: string,
  params: Record<string, any>,
): Promise<any> => {
  const res = await api.post('/mnq9/run-series', { steps: params.steps ?? 60, ...params });
  return res.data;
};

export const fetchMNQ9History = async (
  limit: number = 100,
): Promise<MNQ9Status[]> => {
  // Backend has no /history endpoint; return empty array gracefully
  return [];
};

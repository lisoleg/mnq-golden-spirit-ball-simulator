import api from './client';
import type { MNQ9Status } from './types';

export const fetchMNQ9Status = async (): Promise<MNQ9Status> => {
  const res = await api.get('/mnq9/status');
  return res.data;
};

export const mnq9RunSimulation = async (
  scenario: string,
  params: Record<string, any>,
): Promise<MNQ9Status> => {
  const res = await api.post('/mnq9/simulate', { scenario, ...params });
  return res.data;
};

export const fetchMNQ9History = async (
  limit: number = 100,
): Promise<MNQ9Status[]> => {
  const res = await api.get(`/mnq9/history?limit=${limit}`);
  return res.data;
};

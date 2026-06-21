import api from './client';
import type { MassFaceReadings } from './types';

export const fetchMassfaceReadings = async (): Promise<MassFaceReadings> => {
  const res = await api.get('/massface/readings');
  return res.data;
};

export const fetchMassfaceHistory = async (
  limit: number = 100,
): Promise<MassFaceReadings[]> => {
  const res = await api.get(`/massface/history?limit=${limit}`);
  return res.data;
};

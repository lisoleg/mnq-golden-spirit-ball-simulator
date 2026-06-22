import api from './client';
import type { MassFaceReadings } from './types';

export const fetchMassfaceReadings = async (): Promise<MassFaceReadings> => {
  const res = await api.get('/massface/read');
  return res.data;
};

export const fetchMassfaceHistory = async (
  limit: number = 100,
): Promise<MassFaceReadings[]> => {
  const res = await api.get(`/massface/history?limit=${limit}`);
  const items = res.data.history ?? res.data;
  return (Array.isArray(items) ? items : []).map((item: any) => ({
    ...(item.readings ?? item),
    timestamp: item.timestamp ?? item.readings?.timestamp ?? '',
  }));
};

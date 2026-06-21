import api from './client';
import type { DeepResult } from './types';

export const deepGenerate = async (params: {
  seed_text: string;
  length: number;
  temperature: number;
  syntax_constraint: boolean;
}): Promise<DeepResult> => {
  const res = await api.post('/deep/generate', params);
  return res.data;
};

export const fetchDeepHistory = async (
  limit: number = 50,
): Promise<DeepResult[]> => {
  const res = await api.get(`/deep/history?limit=${limit}`);
  return res.data;
};

import api from './client';
import type { DeepResult } from './types';

export const deepGenerate = async (params: {
  seed_text: string;
  length: number;
  temperature: number;
  syntax_constraint: boolean;
}): Promise<DeepResult> => {
  const res = await api.post('/deep/generate', {
    start_text: params.seed_text,
    length: params.length,
    temperature: params.temperature,
  });
  return res.data;
};

export const fetchDeepHistory = async (
  limit: number = 50,
): Promise<DeepResult[]> => {
  // Backend has no /history endpoint; return empty array gracefully
  return [];
};

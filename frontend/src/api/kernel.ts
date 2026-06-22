import api from './client';
import type { KernelStatus } from './types';

export const fetchKernelStatus = async (): Promise<KernelStatus> => {
  const res = await api.get('/kernel/status');
  return res.data;
};

export const kernelStep = async (steps: number): Promise<KernelStatus> => {
  const res = await api.post('/kernel/step', { steps });
  return res.data;
};

export const kernelReset = async (
  seed?: number,
  condition?: string,
): Promise<KernelStatus> => {
  const res = await api.post('/kernel/reset', { seed, condition });
  return res.data;
};

export const kernelD4Audit = async (): Promise<any> => {
  const res = await api.post('/kernel/d4-audit');
  return res.data;
};

export const fetchKernelField = async (): Promise<any> => {
  const res = await api.get('/kernel/readings');
  return res.data;
};

import api from './client';

export const fetchMeshStatus = async (): Promise<any> => {
  const res = await api.get('/mesh/status');
  return res.data;
};

export const meshStep = async (
  dt: number = 0.016,
  steps: number = 1,
): Promise<any> => {
  const res = await api.post('/mesh/step', { dt, steps });
  return res.data;
};

export const meshSeed = async (
  mode: string = 'background',
  dim: number = 32,
): Promise<any> => {
  const res = await api.post('/mesh/seed', { mode, dim });
  return res.data;
};

export const fetchMeshField = async (): Promise<any> => {
  const res = await api.get('/mesh/field');
  return res.data;
};

export const fetchMeshMassFace = async (): Promise<any> => {
  const res = await api.get('/mesh/mass-face');
  return res.data;
};

export const fetchMeshExcessLoop = async (): Promise<any> => {
  const res = await api.get('/mesh/excess-loop');
  return res.data;
};

import api from './client';

export const fetchMeshStatus = async (): Promise<any> => {
  const res = await api.get('/mesh/status');
  return res.data;
};

export const meshCompute = async (
  params: Record<string, any>,
): Promise<any> => {
  const res = await api.post('/mesh/compute', params);
  return res.data;
};

export const fetchMeshTopology = async (): Promise<any> => {
  const res = await api.get('/mesh/topology');
  return res.data;
};

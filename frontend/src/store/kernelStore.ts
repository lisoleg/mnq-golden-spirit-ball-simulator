import { create } from 'zustand';
import * as kernelApi from '../api/kernel';
import * as massfaceApi from '../api/massface';
import type { KernelStatus, MassFaceReadings } from '../api/types';

interface KernelState {
  status: KernelStatus | null;
  readings: MassFaceReadings | null;
  readingsHistory: MassFaceReadings[];
  loading: boolean;
  error: string | null;
  fetchStatus: () => Promise<void>;
  doStep: (steps: number) => Promise<void>;
  reset: (seed?: number, condition?: string) => Promise<void>;
  doD4Audit: () => Promise<void>;
  fetchReadingsHistory: (limit: number) => Promise<void>;
}

export const useKernelStore = create<KernelState>((set) => ({
  status: null,
  readings: null,
  readingsHistory: [],
  loading: false,
  error: null,

  fetchStatus: async () => {
    set({ loading: true, error: null });
    try {
      const status = await kernelApi.fetchKernelStatus();
      const readings = await massfaceApi.fetchMassfaceReadings();
      set({ status, readings, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  doStep: async (steps) => {
    set({ loading: true, error: null });
    try {
      const status = await kernelApi.kernelStep(steps);
      const readings = await massfaceApi.fetchMassfaceReadings();
      set((s) => ({
        status,
        readings,
        readingsHistory: [...s.readingsHistory.slice(-99), readings],
        loading: false,
      }));
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  reset: async (seed, condition) => {
    set({ loading: true, error: null });
    try {
      const status = await kernelApi.kernelReset(seed, condition);
      set({ status, readingsHistory: [], loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  doD4Audit: async () => {
    set({ loading: true, error: null });
    try {
      await kernelApi.kernelD4Audit();
      const status = await kernelApi.fetchKernelStatus();
      set({ status, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  fetchReadingsHistory: async (limit) => {
    try {
      const history = await massfaceApi.fetchMassfaceHistory(limit);
      set({ readingsHistory: history });
    } catch (e: any) {
      console.error('Failed to fetch readings history:', e);
    }
  },
}));

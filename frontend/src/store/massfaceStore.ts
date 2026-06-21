import { create } from 'zustand';
import * as massfaceApi from '../api/massface';
import type { MassFaceReadings } from '../api/types';

interface MassfaceState {
  readings: MassFaceReadings | null;
  history: MassFaceReadings[];
  loading: boolean;
  error: string | null;
  fetchReadings: () => Promise<void>;
  fetchHistory: (limit: number) => Promise<void>;
}

export const useMassfaceStore = create<MassfaceState>((set) => ({
  readings: null,
  history: [],
  loading: false,
  error: null,

  fetchReadings: async () => {
    set({ loading: true, error: null });
    try {
      const readings = await massfaceApi.fetchMassfaceReadings();
      set((s) => ({
        readings,
        history: [...s.history.slice(-99), readings],
        loading: false,
      }));
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  fetchHistory: async (limit) => {
    set({ loading: true, error: null });
    try {
      const history = await massfaceApi.fetchMassfaceHistory(limit);
      set({ history, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },
}));

import { create } from 'zustand';

interface UIState {
  sidebarCollapsed: boolean;
  currentNav: string;
  toggleSidebar: () => void;
  setNav: (nav: string) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  currentNav: '/',
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setNav: (nav) => set({ currentNav: nav }),
}));

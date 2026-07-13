import { create } from "zustand";
import { UserProfile } from "@/types/api";

interface AppState {
  user: UserProfile | null;
  setUser: (user: UserProfile | null) => void;
  mockMode: boolean;
  setMockMode: (mock: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
  mockMode: false,
  setMockMode: (mock) => set({ mockMode: mock }),
}));

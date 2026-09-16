import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "./types";

type SessionState = {
  token: string | null;
  user: User | null;
  setSession: (token: string, user: User) => void;
  clear: () => void;
};
// Access token lives only in memory. Refresh uses a rotated HttpOnly cookie.
export const useSession = create<SessionState>((set) => ({
  token: null,
  user: null,
  setSession: (token, user) => set({ token, user }),
  clear: () => set({ token: null, user: null }),
}));
export const useCompare = create(
  persist<{ ids: string[]; toggle: (id: string) => void; clear: () => void }>(
    (set) => ({
      ids: [],
      toggle: (id) =>
        set((s) => ({
          ids: s.ids.includes(id)
            ? s.ids.filter((x) => x !== id)
            : [...s.ids.slice(-3), id],
        })),
      clear: () => set({ ids: [] }),
    }),
    { name: "shopilot-comparison" },
  ),
);
export const useNotice = create<{
  text: string;
  show: (text: string) => void;
  clear: () => void;
}>((set) => ({
  text: "",
  show: (text) => set({ text }),
  clear: () => set({ text: "" }),
}));

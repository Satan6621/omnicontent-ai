'use client';

import { create } from 'zustand';
import type { DashboardStats, SocialPost } from '@/types/api';

interface ContentStore {
  lastPost: SocialPost | null;
  stats: DashboardStats | null;
  setLastPost: (post: SocialPost | null) => void;
  setStats: (stats: DashboardStats | null) => void;
}

export const useContentStore = create<ContentStore>((set) => ({
  lastPost: null,
  stats: null,
  setLastPost: (lastPost) => set({ lastPost }),
  setStats: (stats) => set({ stats }),
}));

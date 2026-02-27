import { create } from 'zustand';
// import { supabase } from '../lib/supabase';
import type { StoreState } from '../types';

export const useStore = create<StoreState>((set) => ({
    isInitialized: false,
    isLoading: false,
    error: null,

    fetchData: async () => {
        set({ isLoading: true, error: null });
        try {
            // // Example Supabase fetch:
            // const { data, error } = await supabase.from('your_table').select('*');
            // if (error) throw error;

            // Simulate network delay for template
            await new Promise(resolve => setTimeout(resolve, 300));

            set({ isInitialized: true, isLoading: false });
        } catch (err: any) {
            console.error('Error fetching data:', err);
            set({ error: err.message, isLoading: false });
        }
    }
}));

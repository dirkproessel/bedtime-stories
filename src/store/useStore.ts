import { create } from 'zustand';
import {
    fetchVoices,
    fetchStories,
    generateStory,
    generateFreeStory,
    type VoiceProfile,
    type StoryMeta,
    type StoryRequest,
} from '../lib/api';

interface AppState {
    // Voices
    voices: VoiceProfile[];
    loadVoices: () => Promise<void>;

    // Stories
    stories: StoryMeta[];
    loadStories: () => Promise<void>;

    // Generation
    startGeneration: (req: StoryRequest) => Promise<void>;
    startFreeGeneration: (text: string, voiceKey: string, targetMinutes: number) => Promise<void>;
    pollStatus: () => Promise<void>;
    stopPolling: () => void;
    updateStorySpotify: (id: string, enabled: boolean) => Promise<void>;

    // UI
    activeView: 'create' | 'archive' | 'player';
    setActiveView: (view: 'create' | 'archive' | 'player') => void;
    selectedStoryId: string | null;
    setSelectedStoryId: (id: string | null) => void;

    // Loading
    isLoading: boolean;
    error: string | null;
    isInitialized: boolean;
    fetchData: () => Promise<void>;
}

let pollInterval: ReturnType<typeof setInterval> | null = null;

export const useStore = create<AppState>((set, get) => ({
    voices: [],
    stories: [],
    activeView: 'create',
    selectedStoryId: null,
    isLoading: false,
    error: null,
    isInitialized: false,

    fetchData: async () => {
        set({ isLoading: true, error: null });
        try {
            await Promise.all([get().loadVoices(), get().loadStories()]);
            set({ isInitialized: true });
            get().pollStatus(); // Start polling if any stories are generating
        } catch (e: any) {
            set({ error: e.message || 'Verbindungsfehler' });
        } finally {
            set({ isLoading: false });
        }
    },

    loadVoices: async () => {
        try {
            const voices = await fetchVoices();
            set({ voices });
        } catch {
            // Voices might fail if backend is not running yet – non-critical
        }
    },

    loadStories: async () => {
        try {
            const stories = await fetchStories();
            set({ stories });
        } catch {
            // Same – non-critical on first load
        }
    },

    startGeneration: async (req: StoryRequest) => {
        set({ error: null });
        try {
            await generateStory(req);
            // Immediately switch to archive and reload to show the "Pending" story
            set({ activeView: 'archive' });
            await get().loadStories();
            get().pollStatus();
        } catch (e: any) {
            set({ error: e.message });
        }
    },

    startFreeGeneration: async (text: string, voiceKey: string, targetMinutes: number) => {
        set({ error: null });
        try {
            await generateFreeStory(text, voiceKey, targetMinutes);
            set({ activeView: 'archive' });
            await get().loadStories();
            get().pollStatus();
        } catch (e: any) {
            set({ error: e.message });
        }
    },

    pollStatus: async () => {
        // Clear any existing interval
        if (pollInterval) clearInterval(pollInterval);

        pollInterval = setInterval(async () => {
            const { stories } = get();
            const hasGenerating = stories.some(s => s.status === 'generating');

            if (!hasGenerating) {
                get().stopPolling();
                return;
            }

            try {
                await get().loadStories();
            } catch {
                // Ignore poll errors
            }
        }, 2000);
    },

    stopPolling: () => {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    },

    updateStorySpotify: async (id: string, enabled: boolean) => {
        try {
            const { toggleSpotify } = await import('../lib/api');
            await toggleSpotify(id, enabled);
            set((state) => ({
                stories: state.stories.map((s) =>
                    s.id === id ? { ...s, is_on_spotify: enabled } : s
                ),
            }));
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        }
    },

    setActiveView: (view) => set({ activeView: view }),
    setSelectedStoryId: (id) => set({ selectedStoryId: id }),
}));

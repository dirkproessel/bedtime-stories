import { create } from 'zustand';
import {
    fetchVoices,
    generateStory,
    generateFreeStory,
    loginUser,
    registerUser,
    fetchMe,
    type VoiceProfile,
    type StoryMeta,
    type StoryRequest,
    type User,
} from '../lib/api';

interface AppState {
    // Auth
    user: User | null;
    token: string | null;
    login: (email: string, pass: string) => Promise<void>;
    register: (email: string, pass: string) => Promise<void>;
    logout: () => void;
    fetchUser: () => Promise<void>;

    // Voices
    voices: VoiceProfile[];
    loadVoices: () => Promise<void>;

    // Stories
    stories: StoryMeta[];
    totalStories: number;
    totalMyStories: number;
    totalPublicStories: number;
    currArchivePage: number;
    archiveFilter: 'my' | 'all' | 'public';
    setArchiveFilter: (filter: 'my' | 'all' | 'public') => void;
    loadStories: (page?: number) => Promise<void>;

    // Generation
    startGeneration: (req: StoryRequest) => Promise<void>;
    startFreeGeneration: (text: string, voiceKey: string, targetMinutes: number) => Promise<void>;
    pollStatus: () => Promise<void>;
    stopPolling: () => void;
    updateStorySpotify: (id: string, enabled: boolean) => Promise<void>;

    // UI
    activeView: 'discover' | 'create' | 'library' | 'profile' | 'login';
    setActiveView: (view: 'discover' | 'create' | 'library' | 'profile' | 'login') => void;
    selectedStoryId: string | null;
    setSelectedStoryId: (id: string | null) => void;
    toggleStoryVisibility: (id: string, isPublic: boolean) => Promise<void>;

    // Layer Architecture
    isReaderOpen: boolean;
    readerStoryId: string | null;
    setReaderOpen: (open: boolean, storyId?: string | null) => void;
    
    currentAudioStoryId: string | null;
    showAudioCompanion: boolean;
    setAudioCompanion: (show: boolean, storyId?: string | null) => void;

    // Loading
    isLoading: boolean;
    error: string | null;
    isInitialized: boolean;

    // Generator State (Persistent across views)
    generatorPrompt: string;
    generatorGenre: string;
    generatorAuthors: string[];
    generatorMinutes: number;
    generatorVoice: string;
    generatorParentId: string | null;
    generatorRemixType: 'improvement' | 'sequel' | null;
    generatorContext: { title: string; synopsis: string } | null;
    
    setGeneratorPrompt: (val: string) => void;
    setGeneratorGenre: (val: string) => void;
    setGeneratorAuthors: (val: string[]) => void;
    setGeneratorMinutes: (val: number) => void;
    setGeneratorVoice: (val: string) => void;
    setGeneratorRemix: (parentId: string | null, type: 'improvement' | 'sequel' | null, context?: { title: string; synopsis: string } | null) => void;
    fetchData: () => Promise<void>;

    // Global Modal States
    revoiceStoryId: string | null;
    setRevoiceStoryId: (id: string | null) => void;
}

let pollInterval: ReturnType<typeof setInterval> | null = null;

export const useStore = create<AppState>((set, get) => {
    // Robustly get token
    const storedToken = localStorage.getItem('auth_token');
    const initialToken = (storedToken === 'null' || storedToken === 'undefined') ? null : storedToken;

    return {
    user: null,
    token: initialToken,
    voices: [],
    stories: [],
    totalStories: 0,
    totalMyStories: 0,
    totalPublicStories: 0,
    currArchivePage: 1,
    archiveFilter: 'my',
    setArchiveFilter: (filter) => set({ archiveFilter: filter }),
    activeView: 'create',
    selectedStoryId: null,
    isLoading: false,
    error: null,
    isInitialized: false,

    isReaderOpen: false,
    readerStoryId: null,
    currentAudioStoryId: null,
    showAudioCompanion: false,

    generatorPrompt: '',
    generatorGenre: 'Realismus',
    generatorAuthors: [],
    generatorMinutes: 15,
    generatorVoice: 'seraphina',
    generatorParentId: null,
    generatorRemixType: null,
    generatorContext: null,

    setGeneratorPrompt: (val) => set({ generatorPrompt: val }),
    setGeneratorGenre: (val) => set({ generatorGenre: val }),
    setGeneratorAuthors: (val) => set({ generatorAuthors: val }),
    setGeneratorMinutes: (val) => set({ generatorMinutes: val }),
    setGeneratorVoice: (val) => set({ generatorVoice: val }),
    setGeneratorRemix: (parentId, type, context = null) => set({ 
        generatorParentId: parentId, 
        generatorRemixType: type,
        generatorContext: context
    }),

    login: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
            const data = await loginUser(email, password);
            localStorage.setItem('auth_token', data.access_token);
            set({ token: data.access_token });
            await get().fetchUser();
            get().setActiveView('create');
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        } finally {
            set({ isLoading: false });
        }
    },

    register: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
            await registerUser(email, password);
            await get().login(email, password);
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        } finally {
            set({ isLoading: false });
        }
    },

    logout: () => {
        localStorage.removeItem('auth_token');
        set({ user: null, token: null, stories: [], activeView: 'login' });
        get().stopPolling();
    },

    fetchUser: async () => {
        const { token } = get();
        if (!token) return;
        try {
            const user = await fetchMe();
            set({ user });
        } catch (e) {
            // Invalid token
            get().logout();
        }
    },

    fetchData: async () => {
        set({ isLoading: true, error: null });
        try {
            // Try to fetch user, but don't fail if not logged in
            try {
                await get().fetchUser();
            } catch (e) {
                console.log("Not logged in (Guest Mode)");
            }
            
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

    loadStories: async (page = 1) => {
        const { archiveFilter } = get();
        try {
            const { fetchStories } = await import('../lib/api');
            const { stories, total, total_my, total_public } = await fetchStories(page, 30, archiveFilter);
            set({ 
                stories, 
                totalStories: total, 
                totalMyStories: total_my, 
                totalPublicStories: total_public,
                currArchivePage: page 
            });
        } catch {
            // Same – non-critical on first load
        }
    },

    startGeneration: async (req: StoryRequest) => {
        set({ error: null });
        try {
            await generateStory(req);
            // Reset remix state after starting
            set({ 
                generatorParentId: null, 
                generatorRemixType: null, 
                generatorContext: null 
            });
            // Immediately switch to archive and reload to show the "Pending" story
            set({ activeView: 'library' });
            await get().loadStories();
            get().pollStatus();
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        }
    },

    startFreeGeneration: async (text: string, voiceKey: string, targetMinutes: number) => {
        set({ error: null });
        try {
            await generateFreeStory(text, voiceKey, targetMinutes);
            set({ activeView: 'library' });
            await get().loadStories();
            get().pollStatus();
        } catch (e: any) {
            set({ error: e.message });
            throw e;
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
            const { updateStorySpotify: apiUpdateStorySpotify } = await import('../lib/api');
            await apiUpdateStorySpotify(id, enabled);
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
    setActiveView: (view) => {
        set({ activeView: view });
        // Handle filter auto-sync if switching to library/discover
        if (view === 'library') set({ archiveFilter: 'my' });
        if (view === 'discover') set({ archiveFilter: 'public' });
    },
    setSelectedStoryId: (id) => set({ selectedStoryId: id }),
    setReaderOpen: (open, storyId = null) => set({ 
        isReaderOpen: open, 
        readerStoryId: storyId || get().readerStoryId 
    }),
    setAudioCompanion: (show, storyId = null) => set({ 
        showAudioCompanion: show, 
        currentAudioStoryId: storyId || get().currentAudioStoryId 
    }),
    toggleStoryVisibility: async (id, isPublic) => {
        try {
            const { updateStoryVisibility: apiUpdateVisibility } = await import('../lib/api');
            await apiUpdateVisibility(id, isPublic);
            set((state) => ({
                stories: state.stories.map((s) =>
                    s.id === id ? { ...s, is_public: isPublic } : s
                ),
            }));
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        }
    },
    revoiceStoryId: null,
    setRevoiceStoryId: (id) => set({ revoiceStoryId: id }),
    };
});

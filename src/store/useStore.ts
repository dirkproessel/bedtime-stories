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
    adminFetchUsers,
    adminDeleteUser,
    adminUpdateUser,
    adminDeleteStory,
    adminListVoices,
    adminToggleVoice,
    toggleStoryFavorite,
    revoiceStory as apiRevoiceStory,
    regenerateStoryImage as apiRegenerateStoryImage,
    fetchPlaylist,
    addToPlaylist as apiAddToPlaylist,
    removeFromPlaylist as apiRemoveFromPlaylist,
    clearPlaylist as apiClearPlaylist,
} from '../lib/api';
import { type UserVoice, type SystemVoice } from '../lib/api';

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
    archiveFilter: 'my' | 'all' | 'public' | 'favorites';
    archiveGenre: string[];
    archiveSearch: string | null;
    availableGenres: string[];
    hasMore: boolean;
    setArchiveFilter: (filter: 'my' | 'all' | 'public' | 'favorites') => void;
    setArchiveGenre: (genre: string[]) => void;
    toggleArchiveGenre: (genre: string) => void;
    setArchiveSearch: (search: string | null) => void;
    loadStories: (page?: number, userId?: string, pageSize?: number) => Promise<void>;
    loadMoreStories: (userId?: string, pageSize?: number) => Promise<void>;

    // Generation
    startGeneration: (req: StoryRequest) => Promise<void>;
    startFreeGeneration: (text: string, voiceKey: string, targetMinutes: number) => Promise<void>;
    pollStatus: () => Promise<void>;
    stopPolling: () => void;
    updateStorySpotify: (id: string, enabled: boolean) => Promise<void>;

    // UI
    activeView: 'discover' | 'create' | 'library' | 'favorites' | 'profile' | 'login' | 'admin';
    setActiveView: (view: 'discover' | 'create' | 'library' | 'favorites' | 'profile' | 'login' | 'admin') => void;
    
    // Admin
    adminUsers: User[];
    loadAdminUsers: () => Promise<void>;
    deleteAdminUser: (id: string) => Promise<void>;
    updateAdminUser: (id: string, data: { is_admin?: boolean, is_active?: boolean }) => Promise<void>;
    deleteAdminStory: (id: string) => Promise<void>;
    adminClonedVoices: UserVoice[];
    adminSystemVoices: SystemVoice[];
    loadAdminVoices: () => Promise<void>;
    toggleAdminVoice: (type: 'system' | 'clone', id: string) => Promise<void>;
    selectedStoryId: string | null;
    setSelectedStoryId: (id: string | null) => void;
    adminSubView: 'users' | 'stories' | 'voices' | 'experiment';
    setAdminSubView: (view: 'users' | 'stories' | 'voices' | 'experiment') => void;
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
    revoiceStory: (id: string, voiceKey: string, speechRate?: string) => Promise<void>;
    toggleFavorite: (id: string) => Promise<void>;
    deleteStory: (id: string) => Promise<void>;
    regenerateStoryImage: (id: string, imageHints?: string) => Promise<void>;
    updateStory: (id: string, data: any) => Promise<void>;

    // Alexa Playlist
    playlist: StoryMeta[];
    loadPlaylist: () => Promise<void>;
    addToPlaylist: (storyId: string) => Promise<void>;
    removeFromPlaylist: (storyId: string) => Promise<void>;
    clearPlaylist: () => Promise<void>;
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
    hasMore: true,
    archiveFilter: 'my',
    archiveGenre: [],
    archiveSearch: null,
    availableGenres: [],
    setArchiveFilter: (filter) => set({ archiveFilter: filter }),
    setArchiveGenre: (genre) => set({ archiveGenre: genre }),
    toggleArchiveGenre: (genre) => set((state) => ({ 
        archiveGenre: state.archiveGenre.includes(genre)
            ? state.archiveGenre.filter(g => g !== genre)
            : [...state.archiveGenre, genre]
    })),
    setArchiveSearch: (search) => set({ archiveSearch: search }),
    activeView: 'create',
    adminUsers: [],
    adminClonedVoices: [],
    adminSystemVoices: [],
    selectedStoryId: null,
    adminSubView: 'users',
    isLoading: false,
    error: null,
    isInitialized: false,

    isReaderOpen: false,
    readerStoryId: null,
    currentAudioStoryId: null,
    showAudioCompanion: false,

    generatorPrompt: '',
    generatorGenre: '',
    generatorAuthors: [],
    generatorMinutes: 10,
    generatorVoice: 'none',
    generatorParentId: null,
    generatorRemixType: null,
    generatorContext: null,

    playlist: [],

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
            
            await Promise.all([
                get().loadVoices(), 
                get().loadStories(),
                get().loadPlaylist()
            ]);
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

    loadStories: async (page = 1, userId?: string, pageSize = 20) => {
        const { archiveFilter, archiveGenre, archiveSearch } = get();
        set({ isLoading: true });
        try {
            const { fetchStories } = await import('../lib/api');
            const res = await fetchStories({
                page: page, 
                pageSize: pageSize, 
                filter: archiveFilter, 
                userId: userId,
                genre: archiveGenre.length > 0 ? archiveGenre : undefined,
                search: archiveSearch || undefined
            });
            const { stories, total, total_my, total_public, available_genres } = res;
            set({ 
                stories, 
                totalStories: total,
                totalMyStories: total_my,
                totalPublicStories: total_public,
                currArchivePage: page,
                availableGenres: available_genres || [],
                hasMore: stories.length === pageSize && stories.length < (archiveFilter === 'my' ? total_my : archiveFilter === 'public' ? total_public : total)
            });
        } catch (e: any) {
            set({ error: e.message });
        } finally {
            set({ isLoading: false });
        }
    },

    loadMoreStories: async (userId?: string, pageSize = 20) => {
        const { archiveFilter, archiveGenre, archiveSearch, currArchivePage, stories: existingStories, hasMore, isLoading } = get();
        if (!hasMore || isLoading) return;

        const nextPage = currArchivePage + 1;
        set({ isLoading: true });
        try {
            const { fetchStories } = await import('../lib/api');
            const res = await fetchStories({ 
                page: nextPage, 
                pageSize: pageSize,
                filter: archiveFilter,
                userId: userId,
                genre: archiveGenre.length > 0 ? archiveGenre : undefined,
                search: archiveSearch || undefined
            });
            const { stories: newStories, total, total_my, total_public, available_genres } = res;
            
            const updatedStories = [...existingStories, ...newStories];
            set({ 
                stories: updatedStories,
                totalStories: total,
                totalMyStories: total_my,
                totalPublicStories: total_public,
                currArchivePage: nextPage,
                availableGenres: available_genres || [],
                hasMore: newStories.length === pageSize && updatedStories.length < (archiveFilter === 'my' ? total_my : archiveFilter === 'public' ? total_public : total)
            });
        } catch (e: any) {
            set({ error: e.message });
        } finally {
            set({ isLoading: false });
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
        // Standard scroll to top on view change
        if (typeof window !== 'undefined') {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
        // Handle filter auto-sync if switching to library/discover
        if (view === 'library') {
            get().setArchiveFilter('my');
            get().setArchiveGenre([]);
            get().setArchiveSearch(null);
            get().loadStories(1);
        } else if (view === 'discover') {
            get().setArchiveFilter('public');
            get().setArchiveGenre([]);
            get().setArchiveSearch(null);
            get().loadStories(1);
        } else if (view === 'favorites') {
            get().setArchiveFilter('favorites');
            get().setArchiveGenre([]);
            get().setArchiveSearch(null);
            get().loadStories(1);
        } else if (view === 'admin') {
            get().setArchiveFilter('all');
            get().setArchiveGenre([]);
            get().setArchiveSearch(null);
            get().loadStories(1);
        }
    },
    setSelectedStoryId: (id) => set({ selectedStoryId: id }),
    setAdminSubView: (view) => set({ adminSubView: view }),
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
    revoiceStory: async (id, voiceKey, speechRate = '0%') => {
        set({ error: null });
        try {
            await apiRevoiceStory(id, voiceKey, speechRate);
            // Update local story status to "generating" to show progress UI
            set((state) => ({
                stories: state.stories.map((s) =>
                    s.id === id ? { ...s, status: 'generating', progress: 'Starte Neuvertonung...', progress_pct: 0 } : s
                ),
            }));
            get().pollStatus();
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        }
    },

    loadAdminUsers: async () => {
        set({ isLoading: true });
        try {
            const users = await adminFetchUsers();
            set({ adminUsers: users });
        } catch (e: any) {
            set({ error: e.message });
        } finally {
            set({ isLoading: false });
        }
    },

    deleteAdminUser: async (id) => {
        try {
            await adminDeleteUser(id);
            set(state => ({ adminUsers: state.adminUsers.filter(u => u.id !== id) }));
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        }
    },

    updateAdminUser: async (id, data) => {
        try {
            await adminUpdateUser(id, data);
            set(state => ({
                adminUsers: state.adminUsers.map(u => u.id === id ? { ...u, ...data } : u)
            }));
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        }
    },

    deleteAdminStory: async (id) => {
        try {
            await adminDeleteStory(id);
            set(state => ({
                stories: state.stories.filter(s => s.id !== id)
            }));
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        }
    },

    loadAdminVoices: async () => {
        set({ isLoading: true });
        try {
            const data = await adminListVoices();
            set({ 
                adminClonedVoices: data.clones, 
                adminSystemVoices: data.system 
            });
        } catch (e: any) {
            set({ error: e.message });
        } finally {
            set({ isLoading: false });
        }
    },

    toggleAdminVoice: async (type, id) => {
        try {
            const newState = await adminToggleVoice(type, id);
            set(state => ({
                adminClonedVoices: state.adminClonedVoices.map(v => 
                    (type === 'clone' && v.id === id) ? { ...v, is_public: newState } : v
                ),
                adminSystemVoices: state.adminSystemVoices.map(v => 
                    (type === 'system' && v.id === id) ? { ...v, is_active: newState } : v
                )
            }));
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        }
    },
    toggleFavorite: async (id) => {
        try {
            const { is_favorite } = await toggleStoryFavorite(id);
            set(state => ({
                stories: state.stories.map(s => s.id === id ? { ...s, is_favorite } : s)
            }));
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        }
    },
    deleteStory: async (id) => {
        try {
            const { deleteStory: apiDeleteStory } = await import('../lib/api');
            await apiDeleteStory(id);
            set(state => ({
                stories: state.stories.filter(s => s.id !== id),
                totalMyStories: state.totalMyStories - 1
            }));
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        }
    },
    regenerateStoryImage: async (id, imageHints) => {
        try {
            await apiRegenerateStoryImage(id, imageHints);
            set((state) => ({
                stories: state.stories.map((s) =>
                    s.id === id ? { ...s, status: 'generating', progress: 'Bild wird neu generiert...', progress_pct: 0 } : s
                ),
            }));
            get().pollStatus();
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        }
    },
    updateStory: async (id: string, data: any) => {
        set({ isLoading: true, error: null });
        try {
            const { patchStory } = await import('../lib/api');
            const updated = await patchStory(id, data);
            set((state) => ({
                stories: state.stories.map((s) => s.id === id ? { ...s, ...updated } : s),
            }));
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        } finally {
            set({ isLoading: false });
        }
    },

    loadPlaylist: async () => {
        const { user } = get();
        if (!user || !user.alexa_user_id) return;
        try {
            const playlist = await fetchPlaylist();
            set({ playlist });
        } catch (e) {
            console.error("Failed to load Alexa playlist", e);
        }
    },

    addToPlaylist: async (storyId) => {
        try {
            await apiAddToPlaylist(storyId);
            await get().loadPlaylist();
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        }
    },

    removeFromPlaylist: async (storyId) => {
        try {
            await apiRemoveFromPlaylist(storyId);
            await get().loadPlaylist();
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        }
    },

    clearPlaylist: async () => {
        try {
            await apiClearPlaylist();
            set({ playlist: [] });
        } catch (e: any) {
            set({ error: e.message });
            throw e;
        }
    },
    };
});

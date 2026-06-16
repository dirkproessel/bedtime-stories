/**
 * API client for the Bedtime Stories backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Helper to get auth headers from local storage
function getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('auth_token');
    if (token) {
        return {
            'Authorization': `Bearer ${token}`
        };
    }
    return {};
}

export interface UserVoice {
    id: string;
    user_id: string;
    fish_voice_id: string;
    name: string;
    is_public: boolean;
    gender?: string;
    description?: string;
    created_at: string;
    user_name?: string; // For admin view
}

export interface SystemVoice {
    id: string;
    name: string;
    engine: string;
    gender: string;
    description?: string;
    is_active: boolean;
    fish_voice_id?: string;
}

export interface User {
    id: string;
    email: string;
    is_admin: boolean;
    username: string;
    kindle_email?: string;
    avatar_url?: string;
    created_at: string;
    story_count?: number;
    alexa_user_id?: string;
    whatsapp_phone?: string;
    custom_voice_id?: string; // Legacy
    custom_voice_name?: string; // Legacy
    custom_voices?: UserVoice[];
}

export interface VoiceProfile {
    key: string;
    name: string;
    gender: string;
    engine: string;
    description?: string;
    accent?: string;
    style?: string;
}

export interface StoryMeta {
    id: string;
    title: string;
    description: string;
    prompt: string;
    genre: string;
    style: string;
    voice_key: string;
    duration_seconds: number | null;
    chapter_count: number;
    word_count?: number;
    image_url: string | null;
    is_on_spotify: boolean;
    status: 'generating' | 'done' | 'error';
    progress?: string;
    progress_pct?: number;
    voice_name?: string;
    created_at: string;
    user_id?: string;
    user_email?: string;
    is_public: boolean;
    parent_id?: string;
    updated_at: string;
    highlights?: string;
    is_favorite: boolean;
    multi_voice?: boolean;
}

export interface StoryDetail extends StoryMeta {
    chapters: { title: string; text: string }[];
}

export interface GenerationStatus {
    id: string;
    status: string;
    progress: string;
    progress_pct: number;
    title: string | null;
}

export interface SystemSetting {
    key: string;
    value: string;
    description?: string;
    updated_at: string;
}

export interface StoryRequest {
    prompt: string;
    system_prompt?: string;
    genre?: string;
    style?: string;
    characters?: string[];
    target_minutes?: number;
    voice_key?: string;
    speech_rate?: string;
    parent_id?: string;
    remix_type?: 'improvement' | 'sequel';
    further_instructions?: string;
    multi_voice?: boolean;
}

// --- Auth Endpoints ---
export async function loginUser(email: string, password: string): Promise<{ access_token: string }> {
    const formData = new URLSearchParams();
    formData.append('username', email); // OAuth2 expects username
    formData.append('password', password);

    const res = await fetch(`${API_BASE}/api/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Login fehlgeschlagen');
    }
    return res.json();
}

export async function registerUser(email: string, password: string): Promise<User> {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Registrierung fehlgeschlagen');
    }
    return res.json();
}

export async function registerGuest(): Promise<{ access_token: string, token_type: string, user: User }> {
    const res = await fetch(`${API_BASE}/api/auth/guest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Gast-Login fehlgeschlagen');
    }
    return res.json();
}

export async function upgradeGuest(email: string, password: string): Promise<User> {
    const res = await fetch(`${API_BASE}/api/auth/upgrade-guest`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Account-Upgrade fehlgeschlagen');
    }
    return res.json();
}

export async function loginAndMergeGuest(email: string, password: string): Promise<{ access_token: string, token_type: string }> {
    const res = await fetch(`${API_BASE}/api/auth/login-merge`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Login und Zusammenführen fehlgeschlagen');
    }
    return res.json();
}

export async function fetchMe(): Promise<User> {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
        headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Nicht angemeldet oder Token abgelaufen');
    return res.json();
}

export async function updateKindleEmail(kindle_email: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/auth/me/kindle`, {
        method: 'PUT',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ kindle_email }),
    });
    if (!res.ok) throw new Error('Aktualisierung fehlgeschlagen');
    return res.json();
}

export async function updateUsername(username: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/auth/me/username`, {
        method: 'PUT',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ username }),
    });
    if (!res.ok) throw new Error('Aktualisierung fehlgeschlagen');
    return res.json();
}

export async function linkWhatsAppPhone(phone: string): Promise<any> {
    const formData = new FormData();
    formData.append('phone', phone);
    
    const res = await fetch(`${API_BASE}/api/users/me/link-whatsapp`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData,
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'WhatsApp-Verknüpfung fehlgeschlagen');
    }
    return res.json();
}

export async function updateVoiceName(voice_name: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/auth/me/voice-name`, {
        method: 'PUT',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ voice_name }),
    });
    if (!res.ok) throw new Error('Aktualisierung fehlgeschlagen');
    return res.json();
}

export async function updateCustomVoice(voiceId: string, data: { name?: string, is_public?: boolean }): Promise<User> {
    const res = await fetch(`${API_BASE}/api/auth/me/voices/${voiceId}`, {
        method: 'PUT',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Aktualisierung fehlgeschlagen');
    }
    return res.json();
}

export async function deleteCustomVoice(voiceId: string): Promise<User> {
    const res = await fetch(`${API_BASE}/api/auth/me/voices/${voiceId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Löschen fehlgeschlagen');
    }
    return res.json();
}

export async function uploadProfilePicture(file: Blob): Promise<User> {
    const formData = new FormData();
    formData.append('file', file, 'avatar.jpg');

    const res = await fetch(`${API_BASE}/api/auth/me/avatar`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: formData,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Fehler beim Hochladen des Profilbilds');
    }
    return res.json();
}

export async function cloneVoice(file: File): Promise<User> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE}/api/auth/me/voice-clone`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Fehler beim Stimmen-Klonen');
    }
    return res.json();
}

export async function unlinkAlexa(): Promise<void> {
    const res = await fetch(`${API_BASE}/api/alexa/unlink`, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Failed to unlink Alexa');
    }
}

export async function fetchPlaylist(): Promise<StoryMeta[]> {
    const res = await fetch(`${API_BASE}/api/playlist`, { headers: getAuthHeaders() });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Fehler beim Laden der Playlist');
    }
    return res.json();
}

export async function addToPlaylist(storyId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/playlist/add/${storyId}`, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Konnte nicht zur Playlist hinzugefügt werden');
    }
}

export async function removeFromPlaylist(storyId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/playlist/${storyId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Konnte nicht aus der Playlist entfernt werden');
    }
}

export async function clearPlaylist(): Promise<void> {
    const res = await fetch(`${API_BASE}/api/playlist`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Playlist konnte nicht geleert werden');
    }
}


// --- Content Endpoints ---

// Voices
export async function fetchVoices(): Promise<VoiceProfile[]> {
    const res = await fetch(`${API_BASE}/api/voices`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Failed to fetch voices');
    return res.json();
}

export function getVoicePreviewUrl(voiceKey: string): string {
    return `${API_BASE}/api/voices/${voiceKey}/preview?t=${Date.now()}`;
}

// Story generation
export async function generateStory(req: StoryRequest): Promise<{ id: string }> {
    const res = await fetch(`${API_BASE}/api/stories/generate`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error('Failed to start generation');
    return res.json();
}

export async function generateFreeStory(text: string, voiceKey: string, targetMinutes: number): Promise<{ id: string }> {
    const res = await fetch(`${API_BASE}/api/stories/free`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, voice_key: voiceKey, target_minutes: targetMinutes }),
    });
    if (!res.ok) throw new Error('Failed to start generation');
    return res.json();
}

// Status polling
export async function fetchStatus(storyId: string): Promise<GenerationStatus> {
    const res = await fetch(`${API_BASE}/api/status/${storyId}`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Failed to fetch status');
    return res.json();
}

// Stories
export async function fetchStories(params: {
    page?: number;
    pageSize?: number;
    filter?: string;
    userId?: string;
    genre?: string[];
    search?: string;
}): Promise<{ 
    stories: StoryMeta[], 
    total: number,
    total_my: number,
    total_public: number,
    available_genres: string[]
}> {
    const { page = 1, pageSize = 30, filter = 'all', userId, genre, search } = params;
    let url = `${API_BASE}/api/stories?page=${page}&page_size=${pageSize}&filter=${filter}`;
    if (userId) {
        url += `&user_id=${userId}`;
    }
    if (genre && genre.length > 0) {
        genre.forEach(g => {
            url += `&genre=${encodeURIComponent(g)}`;
        });
    }
    if (search) {
        url += `&search=${encodeURIComponent(search)}`;
    }
    const res = await fetch(url, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Failed to fetch stories');
    return res.json();
}

export async function fetchStory(storyId: string): Promise<StoryDetail> {
    const res = await fetch(`${API_BASE}/api/stories/${storyId}`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Failed to fetch story');
    return res.json();
}

export function getAudioUrl(storyId: string): string {
    const token = localStorage.getItem('auth_token');
    const url = new URL(`${API_BASE}/api/stories/${storyId}/audio`);
    if (token) url.searchParams.append('token', token);
    return url.toString();
}

export function getThumbUrl(storyId: string, version?: string): string {
    const token = localStorage.getItem('auth_token');
    const url = new URL(`${API_BASE}/api/stories/${storyId}/thumb.jpg`);
    if (token) url.searchParams.append('token', token);
    if (version) url.searchParams.append('v', version);
    return url.toString();
}

export function getImageUrl(storyId: string, version?: string): string {
    const token = localStorage.getItem('auth_token');
    const url = new URL(`${API_BASE}/api/stories/${storyId}/image.png`);
    if (token) url.searchParams.append('token', token);
    if (version) url.searchParams.append('v', version);
    return url.toString();
}

export async function deleteStory(storyId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/stories/${storyId}`, { 
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Failed to delete story');
}

export async function updateStorySpotify(id: string, enabled: boolean): Promise<any> {
    const response = await fetch(`${API_BASE}/api/stories/${id}/spotify`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
    });
    if (!response.ok) throw new Error('Failed to update Spotify status');
    return response.json();
}

export async function toggleStoryFavorite(id: string): Promise<{ id: string, is_favorite: boolean }> {
    const response = await fetch(`${API_BASE}/api/stories/${id}/favorite`, {
        method: 'POST',
        headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Fehler beim Favorisieren');
    return response.json();
}

export async function exportStoryToKindle(id: string, email: string): Promise<any> {
    const response = await fetch(`${API_BASE}/api/stories/${id}/export-kindle`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Email-Versand fehlgeschlagen');
    }
    return response.json();
}

export interface SpeakerInfo {
    id: number;
    name: string;
    is_narrator: boolean;
    role: string;
    gender?: string;
}

export async function analyzeStorySpeakers(storyId: string, force: boolean = false): Promise<{ speakers: SpeakerInfo[] }> {
    const res = await fetch(`${API_BASE}/api/stories/${storyId}/analyze-speakers${force ? '?force=true' : ''}`, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Fehler bei der Sprecher-Analyse');
    }
    return res.json();
}

export async function revoiceStory(
    storyId: string, 
    voiceKey: string, 
    speechRate: string = '0%', 
    multiVoice: boolean = false,
    speakerVoices?: Record<number, string>
): Promise<{ id: string }> {
    const res = await fetch(`${API_BASE}/api/stories/${storyId}/revoice`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            voice_key: voiceKey, 
            speech_rate: speechRate, 
            multi_voice: multiVoice,
            speaker_voices: speakerVoices 
        }),
    });
    if (!res.ok) throw new Error('Failed to start re-voicing');
    return res.json();
}

export async function updateStoryVisibility(storyId: string, isPublic: boolean): Promise<StoryMeta> {
    return patchStory(storyId, { is_public: isPublic });
}

export async function patchStory(storyId: string, data: Partial<StoryDetail>): Promise<StoryMeta> {
    const res = await fetch(`${API_BASE}/api/stories/${storyId}`, {
        method: 'PATCH',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Die Geschichte konnte nicht aktualisiert werden');
    }
    return res.json();
}

export async function regenerateStoryImage(storyId: string, imageHints?: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/stories/${storyId}/regenerate-image`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_hints: imageHints }),
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Bild-Regenerierung fehlgeschlagen');
    }
    return res.json();
}

export function getRssFeedUrl(): string {
    return `${API_BASE}/api/feed-labor.xml`;
}

export interface PopularityData {
    genres: string[];   // genre values sorted by usage, desc
    authors: string[];  // author IDs sorted by usage, desc
    voices: string[];   // voice keys sorted by usage, desc
}

export async function fetchPopularity(): Promise<PopularityData> {
    const res = await fetch(`${API_BASE}/api/stats/popularity`);
    if (!res.ok) throw new Error('Failed to fetch popularity');
    return res.json();
}

export async function generateHook(genre: string, authorId: string, userInput?: string): Promise<string> {
    const res = await fetch(`${API_BASE}/api/generate-hook`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ genre, author_id: authorId, user_input: userInput }),
    });
    if (!res.ok) throw new Error('Failed to generate hook');
    const data = await res.json();
    return data.hook_text;
}

// --- Admin Endpoints ---

export async function adminFetchUsers(): Promise<User[]> {
    const res = await fetch(`${API_BASE}/api/admin/users`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Fehler beim Laden der Benutzer');
    return res.json();
}

export async function adminDeleteUser(userId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/admin/users/${userId}`, { 
        method: 'DELETE',
        headers: getAuthHeaders() 
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Benutzer konnte nicht gelöscht werden');
    }
}

export async function adminUpdateUser(userId: string, data: { is_admin?: boolean, is_active?: boolean }): Promise<void> {
    const res = await fetch(`${API_BASE}/api/admin/users/${userId}`, {
        method: 'PATCH',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Benutzer konnte nicht aktualisiert werden');
    }
}

export async function adminDeleteStory(storyId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/admin/stories/${storyId}`, { 
        method: 'DELETE',
        headers: getAuthHeaders() 
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Geschichte konnte nicht gelöscht werden');
    }
}

export async function adminListVoices(): Promise<{ clones: UserVoice[], system: SystemVoice[] }> {
    const res = await fetch(`${API_BASE}/api/admin/voices`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Fehler beim Laden der Stimmen');
    return res.json();
}

export async function adminToggleVoice(type: string, id: string): Promise<boolean> {
    const res = await fetch(`${API_BASE}/api/admin/voices/${type}/${id}/toggle`, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Fehler beim Ändern des Stimmen-Status');
    const data = await res.json();
    return data.new_state;
}

export async function adminFetchSettings(): Promise<SystemSetting[]> {
    const res = await fetch(`${API_BASE}/api/admin/settings`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Fehler beim Laden der Einstellungen');
    return res.json();
}

export async function adminUpdateSetting(key: string, value: string): Promise<SystemSetting> {
    const res = await fetch(`${API_BASE}/api/admin/settings/${key}`, {
        method: 'PATCH',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ value }),
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Einstellung konnte nicht aktualisiert werden');
    }
    return res.json();
}

export async function adminAnalyzeStory(storyId: string): Promise<{
    story_id: string;
    title: string;
    current_synopsis: string;
    new_synopsis: string;
    highlights: string;
}> {
    const res = await fetch(`${API_BASE}/api/admin/analyze-story/${storyId}`, {
        method: 'POST',
        headers: getAuthHeaders(),
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Analyse fehlgeschlagen');
    }
    return res.json();
}

export async function adminAddVoice(data: {
    name: string;
    engine: string;
    gender: string;
    description?: string;
    fish_voice_id?: string;
}): Promise<VoiceProfile> {
    const res = await fetch(`${API_BASE}/api/admin/voices`, {
        method: 'POST',
        headers: {
            ...getAuthHeaders(),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Fehler beim Erstellen der Stimme');
    }
    return res.json();
}

export async function adminUpdateVoice(
    type: 'system' | 'clone',
    id: string,
    data: {
        name?: string;
        engine?: string;
        gender?: string;
        description?: string;
        fish_voice_id?: string;
        is_public?: boolean;
    }
): Promise<any> {
    const res = await fetch(`${API_BASE}/api/admin/voices/${type}/${id}`, {
        method: 'PATCH',
        headers: {
            ...getAuthHeaders(),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Fehler beim Aktualisieren der Stimme');
    }
    return res.json();
}

// --- Pro Book Types ---

export interface BookChapter {
    id: string;
    book_project_id: string;
    chapter_number: number;
    title: string;
    plot_outline: string;
    pov_character?: string | null;
    content: string | null;
    running_summary: string | null;
    feedback: string | null;
    status: 'draft' | 'generating' | 'done' | 'error';
    created_at: string;
    updated_at: string;
}

export interface BookProject {
    id: string;
    user_id: string;
    title: string;
    prompt: string;
    genre: string;
    style: string;
    genre_config?: string | null;
    characters_bible: string | null;
    style_bible: string | null;
    outline: string | null;
    cover_image_url: string | null;
    cover_prompt: string | null;
    // EPUB front/back matter (editable)
    epub_author: string | null;
    epub_dedication: string | null;
    epub_afterword: string | null;
    epub_imprint: string | null;
    status: 'draft' | 'generating' | 'proofreading' | 'completed' | 'error';
    progress: string | null;
    progress_pct: number;
    created_at: string;
    updated_at: string;
}

export interface BookProjectDetail extends BookProject {
    chapters: BookChapter[];
}

export interface KdpMetadata {
    suggested_subtitle: string;
    description_kdp: string;
    search_keywords: string[];
    recommended_bisac_categories: string[];
    pricing_recommendation: {
        price: string;
        reason: string;
    };
}

export interface LektoratFinding {
    category: 'consistency' | 'style' | 'grammar' | 'pacing';
    description: string;
    original_snippet: string;
    suggested_rewrite: string;
}

// --- Pro Book Endpoints ---

export async function fetchProBooks(): Promise<BookProject[]> {
    const res = await fetch(`${API_BASE}/api/pro/books`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Fehler beim Laden der Pro-Buchprojekte');
    return res.json();
}

export async function fetchProBookDetail(id: string): Promise<BookProjectDetail> {
    const res = await fetch(`${API_BASE}/api/pro/books/${id}`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Fehler beim Laden des Buchprojekts');
    return res.json();
}

export async function createProBook(req: { title: string, prompt: string, genre: string, style: string, genre_config?: string }): Promise<BookProject> {
    const res = await fetch(`${API_BASE}/api/pro/books`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error('Fehler beim Erstellen des Buchprojekts');
    return res.json();
}

export async function updateProBook(id: string, data: Partial<BookProject>): Promise<BookProject> {
    const res = await fetch(`${API_BASE}/api/pro/books/${id}`, {
        method: 'PUT',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Fehler beim Aktualisieren des Buchprojekts');
    return res.json();
}

export async function deleteProBook(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/pro/books/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Fehler beim Löschen des Buchprojekts');
}

export async function suggestProCharacters(id: string, model?: string): Promise<{ suggestions: any[] }> {
    let url = `${API_BASE}/api/pro/books/${id}/characters/suggest`;
    if (model) url += `?model=${encodeURIComponent(model)}`;
    const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Fehler beim Generieren der Charakter-Vorschläge');
    return res.json();
}

export async function generateProOutline(
    id: string, 
    numChapters: number = 8, 
    model?: string,
    instruction?: string
): Promise<BookProjectDetail> {
    let url = `${API_BASE}/api/pro/books/${id}/outline?num_chapters=${numChapters}`;
    if (model) url += `&model=${encodeURIComponent(model)}`;
    if (instruction) url += `&instruction=${encodeURIComponent(instruction)}`;
    const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Fehler beim Generieren der Gliederung');
    return res.json();
}

export async function improveProChapterOutline(
    id: string,
    num: number,
    model?: string,
    instruction?: string
): Promise<BookProjectDetail> {
    let url = `${API_BASE}/api/pro/books/${id}/chapters/${num}/outline/improve`;
    const params = [];
    if (model) params.push(`model=${encodeURIComponent(model)}`);
    if (instruction) params.push(`instruction=${encodeURIComponent(instruction)}`);
    if (params.length > 0) url += `?${params.join('&')}`;
    
    const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Fehler beim Verbessern des Kapitelentwurfs');
    return res.json();
}

export async function updateProOutline(id: string, chapters: any[]): Promise<BookProjectDetail> {
    const res = await fetch(`${API_BASE}/api/pro/books/${id}/outline`, {
        method: 'PUT',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(chapters)
    });
    if (!res.ok) throw new Error('Fehler beim Speichern der Gliederung');
    return res.json();
}

export async function generateProChapter(
    id: string, 
    num: number, 
    model?: string, 
    feedback?: string, 
    targetWords?: number
): Promise<{ status: string }> {
    let url = `${API_BASE}/api/pro/books/${id}/chapters/${num}/generate`;
    const params = [];
    if (model) params.push(`model=${encodeURIComponent(model)}`);
    if (feedback) params.push(`feedback=${encodeURIComponent(feedback)}`);
    if (targetWords) params.push(`target_words=${targetWords}`);
    if (params.length > 0) url += `?${params.join('&')}`;
    
    const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error(`Fehler beim Generieren von Kapitel ${num}`);
    return res.json();
}

export async function updateProChapter(id: string, num: number, data: { title?: string, plot_outline?: string, content?: string, feedback?: string }): Promise<BookChapter> {
    const res = await fetch(`${API_BASE}/api/pro/books/${id}/chapters/${num}`, {
        method: 'PUT',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error(`Fehler beim Aktualisieren von Kapitel ${num}`);
    return res.json();
}

export async function proofreadProChapter(id: string, num: number, model?: string, category?: string): Promise<{ findings: LektoratFinding[] }> {
    let url = `${API_BASE}/api/pro/books/${id}/chapters/${num}/proofread`;
    const params = [];
    if (model) params.push(`model=${encodeURIComponent(model)}`);
    if (category) params.push(`category=${encodeURIComponent(category)}`);
    if (params.length > 0) url += `?${params.join('&')}`;
    const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error(`Fehler beim Lektorat von Kapitel ${num}`);
    return res.json();
}

export async function generateProCover(id: string, coverPrompt: string, model?: string): Promise<{ status: string }> {
    let url = `${API_BASE}/api/pro/books/${id}/cover?cover_prompt=${encodeURIComponent(coverPrompt)}`;
    if (model) url += `&model=${encodeURIComponent(model)}`;
    const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Fehler beim Starten der Cover-Generierung');
    return res.json();
}

export function getProCoverUrl(id: string, version?: string): string {
    const token = localStorage.getItem('auth_token');
    const url = new URL(`${API_BASE}/api/pro/books/${id}/cover.jpg`);
    if (token) url.searchParams.append('token', token);
    if (version) url.searchParams.append('v', version);
    return url.toString();
}

export function getProEpubUrl(id: string): string {
    const token = localStorage.getItem('auth_token');
    const url = new URL(`${API_BASE}/api/pro/books/${id}/export/epub`);
    if (token) url.searchParams.append('token', token);
    return url.toString();
}

export function getProTxtUrl(id: string): string {
    const token = localStorage.getItem('auth_token');
    const url = new URL(`${API_BASE}/api/pro/books/${id}/export/txt`);
    if (token) url.searchParams.append('token', token);
    return url.toString();
}

export function getProPdfUrl(id: string): string {
    const token = localStorage.getItem('auth_token');
    const url = new URL(`${API_BASE}/api/pro/books/${id}/export/pdf`);
    if (token) url.searchParams.append('token', token);
    return url.toString();
}

export async function fetchProKdpMetadata(id: string, model?: string): Promise<KdpMetadata> {
    let url = `${API_BASE}/api/pro/books/${id}/export/metadata`;
    if (model) url += `?model=${encodeURIComponent(model)}`;
    const res = await fetch(url, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Fehler beim Generieren der KDP-Metadaten');
    return res.json();
}

export async function cancelProBookGeneration(id: string): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE}/api/pro/books/${id}/cancel`, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Fehler beim Abbrechen der Generierung');
    return res.json();
}

export async function suggestProStyleRefinement(id: string, model?: string): Promise<{ suggested_style: string }> {
    let url = `${API_BASE}/api/pro/books/${id}/style/suggest`;
    if (model) url += `?model=${encodeURIComponent(model)}`;
    const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Fehler beim Generieren des Stil-Vorschlags');
    return res.json();
}

export interface GlobalLektoratFinding {
    category: 'consistency' | 'style' | 'pacing' | 'grammar';
    description: string;
    chapters_involved: number[];
    suggested_fix: string;
}

export async function proofreadProBookGlobally(id: string, model?: string, category?: string): Promise<{ findings: GlobalLektoratFinding[] }> {
    let url = `${API_BASE}/api/pro/books/${id}/proofread/global`;
    const params = [];
    if (model) params.push(`model=${encodeURIComponent(model)}`);
    if (category) params.push(`category=${encodeURIComponent(category)}`);
    if (params.length > 0) url += `?${params.join('&')}`;
    const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Fehler beim globalen Lektorat des Buchs');
    return res.json();
}

export async function applyGlobalFeedbackToOutline(
    id: string, 
    findings: GlobalLektoratFinding[], 
    model?: string
): Promise<any> {
    let url = `${API_BASE}/api/pro/books/${id}/outline/apply-global-feedback`;
    if (model) url += `?model=${encodeURIComponent(model)}`;
    const res = await fetch(url, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ findings })
    });
    if (!res.ok) throw new Error('Fehler beim Einarbeiten des Lektorats-Feedbacks');
    return res.json();
}

export async function proofreadProOutlineGlobally(id: string, model?: string): Promise<{ findings: GlobalLektoratFinding[] }> {
    let url = `${API_BASE}/api/pro/books/${id}/outline/proofread`;
    if (model) url += `?model=${encodeURIComponent(model)}`;
    const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Fehler bei der Konsistenzprüfung der Gliederung');
    return res.json();
}



export async function suggestProCoverPrompt(id: string, model?: string): Promise<{ suggested_prompt: string }> {
    let url = `${API_BASE}/api/pro/books/${id}/cover/suggest`;
    if (model) url += `?model=${encodeURIComponent(model)}`;
    const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Fehler beim Generieren des Cover-Prompts');
    return res.json();
}

export interface EpubMetadataSuggestion {
    epub_author: string;
    epub_dedication: string;
    epub_afterword: string;
    epub_imprint: string;
}

export async function suggestProEpubMetadata(id: string, model?: string): Promise<EpubMetadataSuggestion> {
    let url = `${API_BASE}/api/pro/books/${id}/epub/suggest`;
    if (model) url += `?model=${encodeURIComponent(model)}`;
    const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Fehler beim Generieren der EPUB-Metadaten');
    return res.json();
}


export async function importProOutline(id: string, text: string, model?: string): Promise<BookProjectDetail> {
    let url = `${API_BASE}/api/pro/books/${id}/outline/import`;
    const res = await fetch(url, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, model })
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Fehler beim Importieren der Gliederung');
    }
    return res.json();
}

export async function expandProChapterOutline(id: string, num: number, model?: string): Promise<BookProjectDetail> {
    let url = `${API_BASE}/api/pro/books/${id}/chapters/${num}/outline/expand`;
    if (model) url += `?model=${encodeURIComponent(model)}`;
    const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Fehler beim Erweitern des Kapitels');
    }
    return res.json();
}

export async function expandProOutline(id: string, model?: string): Promise<BookProjectDetail> {
    let url = `${API_BASE}/api/pro/books/${id}/outline/expand`;
    if (model) url += `?model=${encodeURIComponent(model)}`;
    const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Fehler beim Erweitern aller Kapitel');
    }
    return res.json();
}

export async function generateAllProChapters(
    id: string, 
    model?: string, 
    targetWords?: number,
    mode?: string,
    customChapters?: string
): Promise<any> {
    let url = `${API_BASE}/api/pro/books/${id}/generate-all`;
    const params = [];
    if (model) params.push(`model=${encodeURIComponent(model)}`);
    if (targetWords) params.push(`target_words=${targetWords}`);
    if (mode) params.push(`mode=${encodeURIComponent(mode)}`);
    if (customChapters) params.push(`custom_chapters=${encodeURIComponent(customChapters)}`);
    if (params.length > 0) url += `?${params.join('&')}`;
    
    const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Fehler beim Starten der Gesamt-Generierung');
    }
    return res.json();
}

export async function fetchGenreProfile(genre: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/pro/genres/${encodeURIComponent(genre)}/profile`, {
        headers: getAuthHeaders()
    });
    if (!res.ok) {
        throw new Error("Genre-Profil konnte nicht geladen werden");
    }
    return res.json();
}

export async function exportProBookToKindle(id: string, email: string): Promise<any> {
    const response = await fetch(`${API_BASE}/api/pro/books/${id}/export/kindle`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Email-Versand fehlgeschlagen');
    }
    return response.json();
}



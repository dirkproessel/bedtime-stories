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
    custom_voice_id?: string; // Legacy
    custom_voice_name?: string; // Legacy
    custom_voices?: UserVoice[];
}

export interface VoiceProfile {
    key: string;
    name: string;
    gender: string;
    engine: string;
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
    is_favorite: boolean;
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
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Failed to unlink Alexa');
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

export async function revoiceStory(storyId: string, voiceKey: string, speechRate: string = '0%'): Promise<{ id: string }> {
    const res = await fetch(`${API_BASE}/api/stories/${storyId}/revoice`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ voice_key: voiceKey, speech_rate: speechRate }),
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

/**
 * API client for the Bedtime Stories backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
    style: string;
    voice_key: string;
    duration_seconds: number | null;
    chapter_count: number;
    image_url: string | null;
    is_on_spotify: boolean;
    created_at: string;
}

export interface StoryDetail extends StoryMeta {
    chapters: { title: string; text: string }[];
}

export interface GenerationStatus {
    id: string;
    status: string;
    progress: string;
    title: string | null;
}

export interface StoryRequest {
    prompt: string;
    style?: string;
    characters?: string[];
    target_minutes?: number;
    voice_key?: string;
    speech_rate?: string;
}

// Voices
export async function fetchVoices(): Promise<VoiceProfile[]> {
    const res = await fetch(`${API_BASE}/api/voices`);
    if (!res.ok) throw new Error('Failed to fetch voices');
    return res.json();
}

export function getVoicePreviewUrl(voiceKey: string): string {
    return `${API_BASE}/api/voices/${voiceKey}/preview`;
}

// Story generation
export async function generateStory(req: StoryRequest): Promise<{ id: string }> {
    const res = await fetch(`${API_BASE}/api/stories/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error('Failed to start generation');
    return res.json();
}

export async function generateFreeStory(text: string, voiceKey: string, targetMinutes: number): Promise<{ id: string }> {
    const res = await fetch(`${API_BASE}/api/stories/generate-free`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, voice_key: voiceKey, target_minutes: targetMinutes }),
    });
    if (!res.ok) throw new Error('Failed to start generation');
    return res.json();
}

// Status polling
export async function fetchStatus(storyId: string): Promise<GenerationStatus> {
    const res = await fetch(`${API_BASE}/api/status/${storyId}`);
    if (!res.ok) throw new Error('Failed to fetch status');
    return res.json();
}

// Stories
export async function fetchStories(): Promise<StoryMeta[]> {
    const res = await fetch(`${API_BASE}/api/stories`);
    if (!res.ok) throw new Error('Failed to fetch stories');
    const data = await res.json();
    return data.stories;
}

export async function fetchStory(storyId: string): Promise<StoryDetail> {
    const res = await fetch(`${API_BASE}/api/stories/${storyId}`);
    if (!res.ok) throw new Error('Failed to fetch story');
    return res.json();
}

export function getAudioUrl(storyId: string): string {
    return `${API_BASE}/api/stories/${storyId}/audio`;
}

export async function deleteStory(storyId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/stories/${storyId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete story');
}

export async function toggleSpotify(storyId: string, enabled: boolean): Promise<void> {
    const res = await fetch(`${API_BASE}/api/stories/${storyId}/spotify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
    });
    if (!res.ok) {
        const detail = await res.text().catch(() => '');
        throw new Error(`Failed to toggle Spotify status: ${res.status} ${detail}`);
    }
}

export function getRssFeedUrl(): string {
    return `${API_BASE}/api/feed.xml`;
}

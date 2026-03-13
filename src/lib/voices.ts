export interface VoiceMeta {
    name: string;
    desc: string;
    isStandard?: boolean;
}

export const VOICE_META: Record<string, VoiceMeta> = {
    // Edge TTS voices (Standard)
    seraphina: { name: 'Seraphina', desc: 'Warm & melodisch', isStandard: true },
    florian: { name: 'Florian', desc: 'Klar & natürlich', isStandard: true },
    // Gemini voices (KI)
    aoede: { name: 'Lara', desc: 'Leicht & klar' },
    kore: { name: 'Mira', desc: 'Fest & energetisch' },
    sulafat: { name: 'Sofia', desc: 'Warm & überzeugend' },
    algenib: { name: 'Vera', desc: 'Rau & charakterstark' },
    laomedeia: { name: 'Julie', desc: 'Aufgeweckt & neugierig' },
    despina: { name: 'Anna', desc: 'Sanft & fließend' },
    gacrux: { name: 'Bruno', desc: 'Tief & resonant' },
    charon: { name: 'Kai', desc: 'Smooth & sachlich' },
    fenrir: { name: 'Leon', desc: 'Warm & lebendig' },
    orus: { name: 'Lukas', desc: 'Fest & klar' },
    enceladus: { name: 'Emil', desc: 'Sanft & hauchend' },
    puck: { name: 'Tim', desc: 'Aufgeweckt & lebhaft' },
    schedar: { name: 'Walter', desc: 'Gleichmäßig & ruhig' },
    iapetus: { name: 'Thomas', desc: 'Bodenständig & klar' },
    zephyr: { name: 'Robin', desc: 'Hell & frisch' },
    umbriel: { name: 'Alex', desc: 'Entspannt & vielseitig' },
    none: { name: 'Keine Stimme', desc: 'Nur Text generieren', isStandard: true },
};

/** Two standard voice keys, always shown first. */
export const STANDARD_VOICE_KEYS = ['seraphina', 'florian', 'none'];

/** Returns the display name for a voice key, falling back to the key itself. */
export function voiceName(key: string): string {
    return VOICE_META[key]?.name ?? key;
}

/** Returns the character description for a voice key. */
export function voiceDesc(key: string): string {
    return VOICE_META[key]?.desc ?? '';
}

/** Returns true if the voice key is a standard voice. */
export function isStandardVoice(key: string): boolean {
    return VOICE_META[key]?.isStandard === true;
}

import { useState, useRef, useEffect, useMemo } from 'react';
import { useStore } from '../store/useStore';
import { getVoicePreviewUrl, generateHook, fetchPopularity, type PopularityData } from '../lib/api';
import { Sparkles, Mic, MicOff, Play, Pause, Venus, Mars, Users, Loader2, ChevronDown, RefreshCw, Dices } from 'lucide-react';
import { voiceDesc, STANDARD_VOICE_KEYS, isStandardVoice, voiceName } from '../lib/voices';
import { AUTHORS } from '../lib/authors';
import toast from 'react-hot-toast';

export const GENRES = [
    { value: 'Krimi', label: 'Krimi', desc: 'Indizien, Verdächtige, falsche Fährten' },
    { value: 'Abenteuer', label: 'Abenteuer', desc: 'Aufbruch, Hindernisse, Heldenreise' },
    { value: 'Science-Fiction', label: 'Science-Fiction', desc: 'Zukunfts-Technik, fremde Welten' },
    { value: 'Märchen', label: 'Märchen', desc: 'Magische Wesen, Wandlung, Alltagsmagie' },
    { value: 'Komödie', label: 'Komödie', desc: 'Situationskomik, Verwechslungen' },
    { value: 'Thriller', label: 'Thriller', desc: 'Countdown, hohe Spannung, verborgene Gefahr' },
    { value: 'Drama', label: 'Drama', desc: 'Tiefe Dialoge, Fokus auf Freundschaft' },
    { value: 'Grusel', label: 'Grusel', desc: 'Schatten, alte Geheimnisse, Gänsehaut' },
    { value: 'Fantasy', label: 'Fantasy', desc: 'Magie, Quests, fremde Welten' },
    { value: 'Satire', label: 'Satire', desc: 'Gesellschaft im Zerrspiegel' },
    { value: 'Dystopie', label: 'Dystopie', desc: 'Überwachung, Kontrolle, Widerstand' },
    { value: 'Historisch', label: 'Historisch', desc: 'Vergangene Zeiten, echte Kulissen' },
    { value: 'Mythologie', label: 'Mythologie', desc: 'Götter, Helden, Ursprungsgeschichten' },
    { value: 'Roadtrip', label: 'Roadtrip', desc: 'Unterwegs, Begegnungen, Umwege' },
    { value: 'Gute Nacht', label: 'Gute Nacht', desc: 'Sanft, ruhig, zum Einschlafen' },
    { value: 'Fabel', label: 'Fabel', desc: 'Tiere, Moral, Lebensweisheit' },
    { value: 'Modern Romanze', label: 'Modern Romanze', desc: 'Urban, prickelnd, witzig' },
    { value: 'Sinnliche Romanze', label: 'Sinnliche Romanze', desc: 'Gefühlvoll, leise, knisternd' },
    { value: 'Erotik', label: 'Erotik', desc: 'Ästhetisch, leidenschaftlich, intensiv' },
    { value: 'Dark Romance', label: 'Dark Romance', desc: 'Verboten, intensiv, Machtspiele' },
];

const LENGTHS = [
    { value: 5, label: 'Kurz', sub: '~5 Min' },
    { value: 10, label: 'Mittel', sub: '~10 Min' },
    { value: 20, label: 'Lang', sub: '~20 Min' },
];

const MAX_GENRES_VISIBLE = 8;
const MAX_AUTHORS_VISIBLE = 8;
const MAX_PREMIUM_VOICES_VISIBLE = 8;

// Sort items array so that popularIds come first (in order), rest follow in original order.
function sortByPopularity<T>(items: T[], popularIds: string[], getKey: (item: T) => string): T[] {
    if (popularIds.length === 0) return items;
    const popularSet = new Set(popularIds);
    const frontRow = popularIds
        .map(id => items.find(i => getKey(i) === id))
        .filter(Boolean) as T[];
    const rest = items.filter(i => !popularSet.has(getKey(i)));
    return [...frontRow, ...rest];
}

export default function StoryCreator() {
    const { 
        startGeneration, voices, user, setActiveView,
        generatorPrompt: freeText, setGeneratorPrompt: setFreeText,
        generatorGenre: genre, setGeneratorGenre: setGenre,
        generatorAuthors: selectedAuthors, setGeneratorAuthors: setSelectedAuthors,
        generatorMinutes: targetMinutes, setGeneratorMinutes: setTargetMinutes,
        generatorVoice: voiceKey, setGeneratorVoice: setVoiceKey,
        generatorParentId, generatorRemixType, generatorContext, setGeneratorRemix,
        isReaderOpen
    } = useStore();

    const [isAudioEnabled, setIsAudioEnabled] = useState(false);

    const toggleAuthor = (id: string) => {
        setSelectedAuthors(
            selectedAuthors.includes(id) 
                ? selectedAuthors.filter(x => x !== id) 
                : (selectedAuthors.length >= 3 ? selectedAuthors : [...selectedAuthors, id])
        );
    };

    // Popularity-sorted lists
    const [popularity, setPopularity] = useState<PopularityData | null>(null);
    const [showAllGenres, setShowAllGenres] = useState(false);
    const [showAllAuthors, setShowAllAuthors] = useState(false);
    const [showAllVoices, setShowAllVoices] = useState(false);

    useEffect(() => {
        fetchPopularity().then(setPopularity).catch(() => {});
    }, []);

    const sortedGenres = useMemo(() => {
        return sortByPopularity(GENRES, popularity?.genres || [], g => g.value);
    }, [popularity]);

    const sortedAuthors = useMemo(() => {
        const baseSortedAuthors = sortByPopularity(AUTHORS, popularity?.authors || [], a => a.id);
        return [...baseSortedAuthors].sort((a, b) => {
            const aSelected = selectedAuthors.includes(a.id) ? 1 : 0;
            const bSelected = selectedAuthors.includes(b.id) ? 1 : 0;
            if (aSelected !== bSelected) return bSelected - aSelected;

            const aMatches = genre && a.preferredGenres?.includes(genre) ? 1 : 0;
            const bMatches = genre && b.preferredGenres?.includes(genre) ? 1 : 0;
            if (aMatches !== bMatches) return bMatches - aMatches;
            
            return 0;
        });
    }, [popularity, selectedAuthors, genre]);

    const sortedVoices = useMemo(() => {
        return sortByPopularity(voices, popularity?.voices || [], v => v.key);
    }, [voices, popularity]);

    // Input state
    // freeText moved to store
    const [isRolling, setIsRolling] = useState(false);

    // Voice preview
    const [previewVoice, setPreviewVoice] = useState<string | null>(null);
    const audioRef = useRef<HTMLAudioElement>(null);

    // Speech recognition
    const [isListening, setIsListening] = useState(false);
    const recognitionRef = useRef<any>(null);

    const handlePreviewVoice = (key: string) => {
        if (previewVoice === key) {
            audioRef.current?.pause();
            setPreviewVoice(null);
            return;
        }
        setPreviewVoice(key);
        if (audioRef.current) {
            audioRef.current.src = getVoicePreviewUrl(key);
            audioRef.current.play();
            audioRef.current.onended = () => setPreviewVoice(null);
        }
    };

    const handleStartListening = () => {
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (!SpeechRecognition) {
            alert('Spracheingabe wird von deinem Browser nicht unterstützt.');
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.lang = 'de-DE';
        recognition.continuous = true;
        recognition.interimResults = true;

        if (isListening) return;
        const initialText = freeText.trim();

        recognition.onresult = (event: any) => {
            let sessionFinalPart = '';
            let sessionInterimPart = '';
            
            for (let i = 0; i < event.results.length; i++) {
                if (event.results[i].isFinal) {
                    sessionFinalPart += event.results[i][0].transcript;
                } else {
                    sessionInterimPart += event.results[i][0].transcript;
                }
            }
            
            const sessionText = (sessionFinalPart + sessionInterimPart).trim();
            if (sessionText) {
                setFreeText(initialText + (initialText ? ' ' : '') + sessionText);
            }
        };

        recognition.onend = () => setIsListening(false);
        recognition.start();
        recognitionRef.current = recognition;
        setIsListening(true);
    };

    const handleStopListening = () => {
        recognitionRef.current?.stop();
        setIsListening(false);
    };

    const handleDiceClick = async () => {
        if (isRolling) return;

        setIsRolling(true);
        try {
            // Pick a random genre only if empty
            let currentGenre = genre;
            if (!currentGenre) {
                currentGenre = GENRES[Math.floor(Math.random() * GENRES.length)].value;
                setGenre(currentGenre);
                
                // Ensure visibility if hidden in the "further" section
                const isVisible = sortedGenres.slice(0, MAX_GENRES_VISIBLE).some(g => g.value === currentGenre);
                if (!isVisible) setShowAllGenres(true);
            }

            // Pick a random author only if empty
            let activeAuthors = selectedAuthors;
            if (activeAuthors.length === 0) {
                const randomAuthorId = AUTHORS[Math.floor(Math.random() * AUTHORS.length)].id;
                activeAuthors = [randomAuthorId];
                setSelectedAuthors(activeAuthors);
                
                // Ensure visibility if hidden in the "further" section
                const isVisible = sortedAuthors.slice(0, MAX_AUTHORS_VISIBLE).some(a => a.id === randomAuthorId);
                if (!isVisible) setShowAllAuthors(true);
            }

            // Fetch hook from LLM, passing existing text as context
            const hook = await generateHook(currentGenre, activeAuthors[0], freeText.trim());
            setFreeText(hook);

        } catch (error) {
            console.error("Dice error:", error);
            toast.error("Inspiration fehlgeschlagen. Bitte erneut versuchen.");
        } finally {
            setIsRolling(false);
        }
    };
    const handleGenerate = () => {
        if (!user) {
            setActiveView('login');
            toast.error('Bitte melde dich an, um eine Geschichte zu generieren.');
            return;
        }

        const idea = freeText.trim() || (
            generatorRemixType === 'sequel' && generatorContext 
                ? `Fortsetzung von ${generatorContext.title}` 
                : 'Überrasche mich mit einer wunderbaren Geschichte.'
        );
        const selectedGenre = GENRES.find(g => g.value === genre);
        const systemPrompt = `Kurzgeschichte im Genre ${selectedGenre?.label || genre}\n\nIdee: ${idea}`;

        startGeneration({
            prompt: idea,
            system_prompt: systemPrompt,
            genre: selectedGenre?.label || genre,
            style: selectedAuthors.length > 0 ? selectedAuthors.join(',') : 'kehlmann',
            target_minutes: targetMinutes,
            voice_key: voiceKey,
            parent_id: generatorParentId || undefined,
            remix_type: generatorRemixType || undefined
        } as any);
    };

    return (
        <div className="pb-48 lg:pb-24">
            {/* Single column layout – same flow as mobile, just wider tiles */}
            <div className="space-y-5">
                
                {/* MAIN EDITOR / IDEA */}
                <div className="space-y-5">
                    {generatorParentId && (
                        <div className="p-4 bg-accent/20 border-2 border-primary/20 rounded-2xl animate-in slide-in-from-top-4 duration-300">
                            <div className="flex items-center justify-between mb-3 text-primary">
                                <div className="flex items-center gap-2 font-bold text-sm">
                                    <RefreshCw className="w-4 h-4" />
                                    {generatorRemixType === 'sequel' ? 'Remix: Fortsetzung schreiben' : 'Remix: Geschichte verbessern'}
                                </div>
                                <button 
                                    onClick={() => setGeneratorRemix(null, null, null)}
                                    className="text-xs uppercase font-bold tracking-wider px-2 py-1 bg-surface rounded-lg border border-slate-700 hover:border-primary transition-colors hover:text-white"
                                >
                                    Abbrechen
                                </button>
                            </div>
                            {generatorContext && (
                                <div className="bg-surface/60 p-3 rounded-xl border border-primary/10">
                                    <h4 className="font-bold text-sm text-slate-200 truncate">{generatorContext.title}</h4>
                                    <p className="text-xs text-slate-400 line-clamp-2 mt-0.5 leading-relaxed">{generatorContext.synopsis}</p>
                                </div>
                            )}
                        </div>
                    )}

                    <div className="space-y-3">
                        <div className="flex items-center justify-between gap-4">
                            <div className="flex-1 flex items-center gap-2">
                                <h3 className="text-xs uppercase font-bold tracking-wider text-slate-400 shrink-0">Deine Idee</h3>
                            </div>
                            <button
                                onClick={handleDiceClick}
                                disabled={isRolling}
                                className="flex items-center gap-2 px-4 py-2 bg-slate-900/40 border border-slate-800 text-slate-500 rounded-xl hover:text-primary hover:border-primary/40 hover:bg-slate-800 transition-all font-medium text-xs disabled:opacity-50 shadow-sm shrink-0"
                            >
                                {isRolling ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Dices className="w-4 h-4" />}
                                Inspiration
                            </button>
                        </div>
                        
                        <div className="relative group">
                            <textarea
                                value={freeText}
                                onChange={(e) => setFreeText(e.target.value)}
                                placeholder="Was soll passieren? Beschreibe Charakter, Ort oder den ersten Satz..."
                                className="w-full px-5 py-4 bg-slate-800/40 border-2 border-slate-700/50 rounded-2xl text-sm lg:text-base focus:outline-none focus:border-primary transition-all placeholder:text-slate-500 resize-none pr-5 lg:pr-16 text-text min-h-[140px] lg:min-h-[160px] shadow-inner"
                            />
                            <button
                                onClick={isListening ? handleStopListening : handleStartListening}
                                className={`absolute right-3 top-4 p-2.5 rounded-xl transition-all hidden lg:flex ${isListening
                                    ? 'bg-red-500 text-white'
                                    : 'bg-surface text-slate-500 hover:text-primary border border-slate-800'
                                    }`}
                                title={isListening ? 'Aufnahme stoppen' : 'Spracheingabe'}
                            >
                                {isListening ? <MicOff className="w-5 h-5 animate-pulse" /> : <Mic className="w-5 h-5" />}
                            </button>
                            
                            {/* Inline Generate Button removed to use floating version */}
                        </div>
                    </div>
                </div>

                {/* SETTINGS – below editor, full width */}
                <div className="space-y-5">
                    
                    {/* Genre */}
                    <div>
                        <div className="mb-1.5 flex items-center gap-2">
                                <h3 className="text-xs uppercase font-bold tracking-wider text-slate-400">Genre</h3>
                        </div>
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                            {(showAllGenres ? sortedGenres : sortedGenres.slice(0, MAX_GENRES_VISIBLE)).map(g => (
                                <button
                                    key={g.value}
                                    onClick={() => setGenre(g.value)}
                                    className={`p-3 rounded-xl text-left transition-all border-2 h-full flex flex-col min-h-[80px] ${genre === g.value
                                        ? 'border-primary bg-primary/10'
                                        : 'border-slate-700/50 bg-slate-800/60 text-slate-400 hover:border-slate-600'
                                        }`}
                                >
                                    <h4 className={`text-sm font-bold tracking-tight ${genre === g.value ? 'text-white' : 'text-slate-300'}`}>{g.label}</h4>
                                    <div className={`text-xs mt-0.5 leading-tight ${genre === g.value ? 'text-white/80' : 'text-slate-500'}`}>{g.desc}</div>
                                </button>
                            ))}
                        </div>
                        {!showAllGenres && sortedGenres.length > MAX_GENRES_VISIBLE && (
                            <button
                                onClick={() => setShowAllGenres(true)}
                                className="mt-2 w-full py-2 rounded-xl border border-dashed border-slate-800 text-xs uppercase font-bold text-slate-500 hover:border-slate-600 hover:text-slate-400 transition-all flex items-center justify-center gap-1"
                            >
                                <ChevronDown className="w-3 h-3" />
                                Weitere Genres
                            </button>
                        )}
                    </div>

                    {/* Authors */}
                    <div>
                        <div className="mb-1.5 flex flex-col gap-0.5">
                                <h3 className="text-xs uppercase font-bold tracking-wider text-slate-400">Stil (Mixe bis zu 3 Autoren)</h3>
                        </div>
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                            {(showAllAuthors ? sortedAuthors : sortedAuthors.slice(0, MAX_AUTHORS_VISIBLE)).map(s => {
                                const isSelected = selectedAuthors.includes(s.id);
                                return (
                                    <button
                                        key={s.id}
                                        onClick={() => toggleAuthor(s.id)}
                                        className={`relative p-3 rounded-xl text-left transition-all border-2 h-full flex flex-col min-h-[80px] group/author ${isSelected
                                            ? 'border-primary bg-primary/10'
                                            : 'border-slate-700/50 bg-slate-800/60 hover:border-slate-600 text-slate-300'
                                            }`}
                                    >
                                        {isSelected && selectedAuthors.length > 1 && (
                                            <div className="absolute -top-2 -right-1.5 px-2 py-0.5 bg-primary text-[9px] font-bold uppercase tracking-tight text-white rounded-lg shadow-lg border border-white/20 z-10 animate-in zoom-in-50 duration-200">
                                                {selectedAuthors.indexOf(s.id) === 0 ? '1. Wortwahl' : 
                                                 selectedAuthors.indexOf(s.id) === 1 ? '2. Atmosphäre' : '3. Erzählweise'}
                                            </div>
                                        )}
                                        <h4 className={`text-sm font-bold tracking-tight ${isSelected ? 'text-white' : 'text-slate-300'}`}>{s.name}</h4>
                                        <div className={`text-xs mt-0.5 ${isSelected ? 'text-white/80' : 'text-slate-500'}`}>{s.desc}</div>
                                    </button>
                                );
                            })}
                        </div>
                        {!showAllAuthors && sortedAuthors.length > MAX_AUTHORS_VISIBLE && (
                            <button
                                onClick={() => setShowAllAuthors(true)}
                                className="mt-2 w-full py-2 rounded-xl border border-dashed border-slate-800 text-xs font-bold text-slate-500 hover:border-slate-600 hover:text-slate-400 transition-all flex items-center justify-center gap-1"
                            >
                                <ChevronDown className="w-3 h-3" />
                                Mehr Autoren
                            </button>
                        )}
                    </div>

                    {/* Voice & Length */}
                    <div className="space-y-5">
                        <div>
                                <div className="mb-1.5 flex items-center gap-2">
                                <h3 className="text-xs uppercase font-bold tracking-wider text-slate-400">Dauer</h3>
                            </div>
                            <div className="grid grid-cols-3 gap-2">
                                {LENGTHS.map(l => (
                                    <button
                                        key={l.value}
                                        onClick={() => setTargetMinutes(l.value)}
                                        className={`p-2 rounded-xl text-center transition-all border-2 h-full flex flex-col justify-center min-h-[64px] ${targetMinutes === l.value
                                            ? 'border-primary bg-primary/10'
                                            : 'border-slate-700/50 bg-slate-800/60 hover:border-slate-600'
                                            }`}
                                    >
                                        <div className={`text-sm font-bold tracking-tight ${targetMinutes === l.value ? 'text-white' : 'text-slate-300'}`}>{l.label}</div>
                                        <div className={`text-xs ${targetMinutes === l.value ? 'text-white/80' : 'text-slate-500'}`}>{l.sub}</div>
                                    </button>
                                ))}
                            </div>
                        </div>
                        {/* Vertonung Toggle */}
                        <div className="flex items-center justify-between p-4 bg-slate-800/40 border-2 border-slate-700/50 rounded-2xl">
                            <div className="flex items-center gap-3">
                                <div className={`p-2 rounded-lg ${isAudioEnabled ? 'bg-primary/20 text-primary' : 'bg-slate-700/50 text-slate-500'}`}>
                                    {isAudioEnabled ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
                                </div>
                                <div>
                                    <h4 className="text-sm font-bold text-slate-200">Vertonung</h4>
                                    <p className="text-xs text-slate-500">Geschichte als Audio generieren</p>
                                </div>
                            </div>
                            <button
                                onClick={() => {
                                    const next = !isAudioEnabled;
                                    setIsAudioEnabled(next);
                                    if (!next) setVoiceKey('none');
                                    else if (voiceKey === 'none') setVoiceKey('marlene'); // Default to something if enabled
                                }}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${isAudioEnabled ? 'bg-primary' : 'bg-slate-700'}`}
                            >
                                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${isAudioEnabled ? 'translate-x-6' : 'translate-x-1'}`} />
                            </button>
                        </div>

                        {isAudioEnabled && (
                            <div className="space-y-5 animate-in slide-in-from-top-4 duration-300">
                                <div>
                                    <div className="mb-1.5 flex items-center gap-2">
                                        <h3 className="text-xs uppercase font-bold tracking-wider text-slate-400">Erzähler</h3>
                                    </div>
                                    <div className="space-y-3">
                                        {/* Standard Voices */}
                                        <div className="space-y-3">
                                            <div className="mb-1.5 flex items-center gap-2">
                                                <h4 className="text-xs font-bold tracking-wider text-slate-500">Standard-Stimmen</h4>
                                            </div>
                                            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                                            {voices
                                                .filter(v => STANDARD_VOICE_KEYS.includes(v.key))
                                                .filter(v => !isAudioEnabled || v.key !== 'none')
                                                .sort((a, b) => STANDARD_VOICE_KEYS.indexOf(a.key) - STANDARD_VOICE_KEYS.indexOf(b.key))
                                                .map(v => (
                                                <div
                                                    key={v.key}
                                                    className={`p-3 rounded-xl transition-all border-2 cursor-pointer h-full min-h-[96px] flex flex-col justify-between gap-1 ${voiceKey === v.key
                                                        ? 'border-primary bg-primary/10'
                                                        : 'border-slate-700/50 bg-slate-800/60 hover:border-slate-600'
                                                        }`}
                                                    onClick={() => setVoiceKey(v.key)}
                                                >
                                                    <div className="flex items-center justify-between w-full">
                                                        <div className="flex items-center gap-1.5 min-w-0">
                                                            <h4 className={`text-sm font-bold truncate tracking-tight ${voiceKey === v.key ? 'text-white' : 'text-slate-300'}`}>
                                                                {voiceName(v.key) !== v.key ? voiceName(v.key) : v.name}
                                                            </h4>
                                                            <div className={`${voiceKey === v.key ? 'text-white' : 'text-slate-600'}`}>
                                                                {v.gender === 'female' ? <Venus className="w-3.5 h-3.5" /> :
                                                                    v.gender === 'male' ? <Mars className="w-3.5 h-3.5" /> : <Users className="w-3.5 h-3.5" />}
                                                            </div>
                                                        </div>
                                                        <button
                                                            onClick={(e) => { e.stopPropagation(); handlePreviewVoice(v.key); }}
                                                            className={`w-7 h-7 rounded-full flex items-center justify-center transition-all shrink-0 ${previewVoice === v.key ? 'bg-primary text-white' : 'bg-slate-800 text-slate-500 border border-slate-700/50'}`}
                                                        >
                                                            {previewVoice === v.key ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 ml-0.5" />}
                                                        </button>
                                                    </div>
                                                    <div className={`text-xs line-clamp-2 leading-tight ${voiceKey === v.key ? 'text-white/80' : 'text-slate-500'}`}>
                                                        {v.description || voiceDesc(v.key)}
                                                    </div>
                                                </div>
                                            ))}
                                            </div>
                                        </div>

                                        {/* Premium Voices */}
                                        <div className="space-y-3">
                                            <div className="flex items-center gap-2 mb-1.5">
                                                <h4 className="text-xs font-bold tracking-wider text-slate-500">Premium-Stimmen</h4>
                                            </div>
                                            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                                                {sortedVoices
                                                    .filter(v => !isStandardVoice(v.key))
                                                    .slice(0, showAllVoices ? sortedVoices.length : MAX_PREMIUM_VOICES_VISIBLE)
                                                    .map(v => (
                                                    <div
                                                        key={v.key}
                                                        className={`p-3 rounded-xl transition-all border-2 cursor-pointer h-full min-h-[96px] flex flex-col justify-between gap-1 ${voiceKey === v.key
                                                            ? 'border-primary bg-primary/10'
                                                            : 'border-slate-700/50 bg-slate-800/60 hover:border-slate-600'
                                                            }`}
                                                        onClick={() => setVoiceKey(v.key)}
                                                    >
                                                        <div className="flex items-center justify-between w-full">
                                                            <div className="flex items-center gap-1.5 min-w-0">
                                                                <h4 className={`text-sm font-bold truncate tracking-tight ${voiceKey === v.key ? 'text-white' : 'text-slate-300'}`}>
                                                                    {voiceName(v.key) !== v.key ? voiceName(v.key) : v.name}
                                                                </h4>
                                                                <div className={`${voiceKey === v.key ? 'text-white' : 'text-slate-600'}`}>
                                                                    {v.gender === 'female' ? <Venus className="w-3.5 h-3.5" /> :
                                                                        v.gender === 'male' ? <Mars className="w-3.5 h-3.5" /> : <Users className="w-3.5 h-3.5" />}
                                                                </div>
                                                            </div>
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handlePreviewVoice(v.key); }}
                                                                className={`w-7 h-7 rounded-full flex items-center justify-center transition-all shrink-0 ${previewVoice === v.key ? 'bg-primary text-white' : 'bg-slate-800 text-slate-500 border border-slate-700/50'}`}
                                                            >
                                                                {previewVoice === v.key ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3 ml-0.5" />}
                                                            </button>
                                                        </div>
                                                        <div className={`text-xs line-clamp-2 leading-tight ${voiceKey === v.key ? 'text-white/80' : 'text-slate-500'}`}>
                                                            {v.description || voiceDesc(v.key)}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                            {sortedVoices.filter(v => !isStandardVoice(v.key)).length > MAX_PREMIUM_VOICES_VISIBLE && (
                                                <button 
                                                    onClick={() => setShowAllVoices(!showAllVoices)}
                                                    className="w-full flex items-center justify-center gap-2 p-2 rounded-xl border border-slate-800 text-xs font-bold text-slate-500 hover:text-slate-400 transition-all bg-slate-800/20"
                                                >
                                                    <span>{showAllVoices ? 'Weniger anzeigen' : `Alle Premiumstimmen (${sortedVoices.filter(v => !isStandardVoice(v.key)).length})`}</span>
                                                    <ChevronDown className={`w-3 h-3 transition-transform ${showAllVoices ? 'rotate-180' : ''}`} />
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Unified Floating Generate Button */}
            {!isReaderOpen && (
                <div className="fixed bottom-22 lg:bottom-12 left-0 right-0 flex justify-center z-[110] pointer-events-none px-4">
                    <div className="pointer-events-auto relative">
                        <div className="absolute -inset-2 bg-background/40 backdrop-blur-xl rounded-full -z-10 border border-white/10 shadow-2xl" />
                        <button
                            onClick={handleGenerate}
                            className="btn-primary px-10 py-4 lg:px-14 lg:py-5 text-lg lg:text-xl shadow-2xl hover:scale-105 active:scale-95 transition-all"
                        >
                            <Sparkles className="w-5 h-5 lg:w-7 lg:h-7 shrink-0" />
                            Geschichte erstellen
                        </button>
                    </div>
                </div>
            )}

            <audio ref={audioRef} className="hidden" />
        </div>
    );
}

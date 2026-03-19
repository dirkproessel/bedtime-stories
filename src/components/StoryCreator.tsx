import { useState, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { getVoicePreviewUrl, generateHook, fetchPopularity } from '../lib/api';
import { Sparkles, Mic, MicOff, Play, Pause, Venus, Mars, Users, Loader2, ChevronDown, RefreshCw, Dices } from 'lucide-react';
import { voiceName, voiceDesc, STANDARD_VOICE_KEYS, isStandardVoice } from '../lib/voices';
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
    { value: 10, label: '~10 Min', sub: '2 Kapitel' },
    { value: 15, label: '~15 Min', sub: '3 Kapitel' },
    { value: 20, label: '~20 Min', sub: '4 Kapitel' },
];

const BEST_OF_COUNT = 8;

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
        generatorParentId, generatorRemixType, generatorContext, setGeneratorRemix
    } = useStore();

    const toggleAuthor = (id: string) => {
        setSelectedAuthors(
            selectedAuthors.includes(id) 
                ? selectedAuthors.filter(x => x !== id) 
                : (selectedAuthors.length >= 3 ? selectedAuthors : [...selectedAuthors, id])
        );
    };

    // Popularity-sorted lists
    const [sortedGenres, setSortedGenres] = useState(GENRES);
    const [sortedAuthors, setSortedAuthors] = useState(AUTHORS);
    const [sortedVoices, setSortedVoices] = useState(voices);
    const [showAllGenres, setShowAllGenres] = useState(false);
    const [showAllAuthors, setShowAllAuthors] = useState(false);
    const [showAllVoices, setShowAllVoices] = useState(false);

    useEffect(() => {
        fetchPopularity()
            .then(data => {
                setSortedGenres(sortByPopularity(GENRES, data.genres, g => g.value));
                setSortedAuthors(sortByPopularity(AUTHORS, data.authors, a => a.id));
                if (data.voices?.length > 0) {
                    setSortedVoices(sortByPopularity(voices, data.voices, v => v.key));
                } else {
                    setSortedVoices(voices);
                }
            })
            .catch(() => { /* keep default order on failure */ });
    }, [voices]);

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

        recognition.onresult = (event: any) => {
            let transcript = '';
            for (let i = 0; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            setFreeText(transcript);
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
                const isVisible = sortedGenres.slice(0, BEST_OF_COUNT).some(g => g.value === currentGenre);
                if (!isVisible) setShowAllGenres(true);
            }

            // Pick a random author only if empty
            let activeAuthors = selectedAuthors;
            if (activeAuthors.length === 0) {
                const randomAuthorId = AUTHORS[Math.floor(Math.random() * AUTHORS.length)].id;
                activeAuthors = [randomAuthorId];
                setSelectedAuthors(activeAuthors);
                
                // Ensure visibility if hidden in the "further" section
                const isVisible = sortedAuthors.slice(0, BEST_OF_COUNT).some(a => a.id === randomAuthorId);
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
        <div className="pb-32 lg:pb-8">
            {/* Single column layout – same flow as mobile, just wider tiles */}
            <div className="space-y-8">
                
                {/* MAIN EDITOR / IDEA */}
                <div className="space-y-8">
                    {generatorParentId && (
                        <div className="p-4 bg-accent/20 border-2 border-primary/20 rounded-2xl animate-in slide-in-from-top-4 duration-300">
                            <div className="flex items-center justify-between mb-3 text-primary">
                                <div className="flex items-center gap-2 font-bold text-sm">
                                    <RefreshCw className="w-4 h-4" />
                                    {generatorRemixType === 'sequel' ? 'Remix: Fortsetzung schreiben' : 'Remix: Geschichte verbessern'}
                                </div>
                                <button 
                                    onClick={() => setGeneratorRemix(null, null, null)}
                                    className="text-[10px] uppercase font-bold tracking-wider px-2 py-1 bg-surface rounded-lg border border-slate-700 hover:border-primary transition-colors hover:text-white"
                                >
                                    Abbrechen
                                </button>
                            </div>
                            {generatorContext && (
                                <div className="bg-surface/60 p-3 rounded-xl border border-primary/10">
                                    <h4 className="font-bold text-xs text-slate-200 truncate">{generatorContext.title}</h4>
                                    <p className="text-[10px] text-slate-400 line-clamp-2 mt-0.5 leading-relaxed">{generatorContext.synopsis}</p>
                                </div>
                            )}
                        </div>
                    )}

                    <div className="space-y-4">
                        <div className="flex items-center justify-between gap-4">
                            <div className="flex-1 flex items-center gap-2">
                                <h3 className="status-label text-primary shrink-0">Deine Idee</h3>
                                <div className="h-px flex-1 bg-slate-800/50" />
                            </div>
                            <button
                                onClick={handleDiceClick}
                                disabled={isRolling}
                                className="flex items-center gap-2 px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-xl hover:text-primary hover:border-primary/40 hover:bg-slate-700 transition-all font-semibold text-xs disabled:opacity-50 shadow-sm shrink-0"
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
                                className="w-full px-5 py-4 bg-background border-2 border-slate-800 rounded-2xl text-xs lg:text-sm focus:outline-none focus:border-primary transition-all placeholder:text-slate-700 resize-none pr-16 font-serif text-text min-h-[160px] lg:min-h-[220px] shadow-inner"
                            />
                            <button
                                onClick={isListening ? handleStopListening : handleStartListening}
                                className={`absolute right-3 top-4 p-2.5 rounded-xl transition-all ${isListening
                                    ? 'bg-red-500 text-white'
                                    : 'bg-surface text-slate-500 hover:text-primary border border-slate-800'
                                    }`}
                                title={isListening ? 'Aufnahme stoppen' : 'Spracheingabe'}
                            >
                                {isListening ? <MicOff className="w-5 h-5 animate-pulse" /> : <Mic className="w-5 h-5" />}
                            </button>
                            
                            {/* Desktop Generate Button */}
                            <div className="hidden lg:flex mt-6 justify-end">
                                <button
                                    onClick={handleGenerate}
                                    className="btn-primary group/btn px-10 py-4 text-xl font-serif shadow-xl hover:shadow-primary/20"
                                >
                                    <Sparkles className="w-6 h-6 group-hover/btn:rotate-12 transition-transform" />
                                    Geschichte erschaffen
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* SETTINGS – below editor, full width */}
                <div className="space-y-8">
                    
                    {/* Genre */}
                    <div>
                        <div className="mb-3 flex items-center gap-2">
                            <h3 className="status-label text-primary">Genre</h3>
                            <div className="h-px flex-1 bg-slate-800/50" />
                        </div>
                        <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
                            {(showAllGenres ? sortedGenres : sortedGenres.slice(0, BEST_OF_COUNT)).map(g => (
                                <button
                                    key={g.value}
                                    onClick={() => setGenre(g.value)}
                                    className={`p-3 rounded-xl text-left transition-all border-2 ${genre === g.value
                                        ? 'border-primary bg-primary/10'
                                        : 'border-slate-700 bg-slate-800/60 text-slate-400 hover:border-slate-600'
                                        }`}
                                >
                                    <h4 className={`text-sm font-bold tracking-tight ${genre === g.value ? 'text-primary' : 'text-slate-300'}`}>{g.label}</h4>
                                    <div className={`text-[11px] mt-0.5 leading-tight ${genre === g.value ? 'text-primary/70' : 'text-slate-500'}`}>{g.desc}</div>
                                </button>
                            ))}
                        </div>
                        {!showAllGenres && sortedGenres.length > BEST_OF_COUNT && (
                            <button
                                onClick={() => setShowAllGenres(true)}
                                className="mt-2 w-full py-2 rounded-xl border border-dashed border-slate-800 text-[10px] uppercase font-bold text-slate-500 hover:border-slate-600 hover:text-slate-400 transition-all flex items-center justify-center gap-1"
                            >
                                <ChevronDown className="w-3 h-3" />
                                Weitere Genres
                            </button>
                        )}
                    </div>

                    {/* Authors */}
                    <div>
                        <div className="mb-3 flex items-center gap-2">
                            <h3 className="status-label text-primary">Stil</h3>
                            <div className="h-px flex-1 bg-slate-800/50" />
                        </div>
                        <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
                            {(showAllAuthors ? sortedAuthors : sortedAuthors.slice(0, BEST_OF_COUNT)).map(s => {
                                const isSelected = selectedAuthors.includes(s.id);
                                return (
                                    <button
                                        key={s.id}
                                        onClick={() => toggleAuthor(s.id)}
                                        className={`relative p-3 rounded-xl text-left transition-all border-2 ${isSelected
                                            ? 'border-primary bg-primary/10'
                                            : 'border-slate-700 bg-slate-800/60 hover:border-slate-600 text-slate-300'
                                            }`}
                                    >
                                        <h4 className={`text-sm font-bold ${isSelected ? 'text-text' : 'text-slate-300'}`}>{s.name}</h4>
                                        <div className={`text-[11px] mt-0.5 ${isSelected ? 'text-primary' : 'text-slate-500'}`}>{s.desc}</div>
                                    </button>
                                );
                            })}
                        </div>
                        {!showAllAuthors && sortedAuthors.length > BEST_OF_COUNT && (
                            <button
                                onClick={() => setShowAllAuthors(true)}
                                className="mt-2 w-full py-2 rounded-xl border border-dashed border-slate-800 text-[10px] font-bold text-slate-500 hover:border-slate-600 hover:text-slate-400 transition-all flex items-center justify-center gap-1"
                            >
                                <ChevronDown className="w-3 h-3" />
                                Mehr Autoren
                            </button>
                        )}
                    </div>

                    {/* Voice & Length */}
                    <div className="space-y-8">
                        <div>
                             <div className="mb-3 flex items-center gap-2">
                                <h3 className="status-label text-primary">Dauer</h3>
                                <div className="h-px flex-1 bg-slate-800/50" />
                            </div>
                            <div className="grid grid-cols-3 gap-2">
                                {LENGTHS.map(l => (
                                    <button
                                        key={l.value}
                                        onClick={() => setTargetMinutes(l.value)}
                                        className={`p-2 rounded-xl text-center transition-all border-2 ${targetMinutes === l.value
                                            ? 'border-primary bg-primary/10'
                                            : 'border-slate-700 bg-slate-800/60 hover:border-slate-600'
                                            }`}
                                    >
                                        <div className={`text-xs font-bold ${targetMinutes === l.value ? 'text-primary' : 'text-slate-300'}`}>{l.label}</div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div>
                            <div className="mb-3 flex items-center gap-2">
                                <h3 className="status-label text-primary">Erzähler</h3>
                                <div className="h-px flex-1 bg-slate-800/50" />
                            </div>
                            <div className="space-y-4">
                                {/* Standard Voices */}
                                <div className="grid grid-cols-2 gap-2">
                                    {voices
                                        .filter(v => STANDARD_VOICE_KEYS.includes(v.key))
                                        .sort((a, b) => STANDARD_VOICE_KEYS.indexOf(a.key) - STANDARD_VOICE_KEYS.indexOf(b.key))
                                        .map(v => (
                                        <div
                                            key={v.key}
                                            className={`p-3 rounded-xl transition-all border-2 cursor-pointer ${voiceKey === v.key
                                                ? 'border-primary bg-primary/10'
                                                : 'border-slate-700 bg-slate-800/60 hover:border-slate-600'
                                                }`}
                                            onClick={() => setVoiceKey(v.key)}
                                        >
                                            <div className="flex flex-col gap-3">
                                                <div className="flex items-center justify-between w-full">
                                                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${voiceKey === v.key ? 'bg-primary/20 text-primary' : 'bg-slate-900 text-slate-600'}`}>
                                                        {v.gender === 'female' ? <Venus className="w-4 h-4" /> :
                                                            v.gender === 'male' ? <Mars className="w-4 h-4" /> : <Users className="w-4 h-4" />}
                                                    </div>
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); handlePreviewVoice(v.key); }}
                                                        className={`w-7 h-7 rounded-full flex items-center justify-center transition-all ${previewVoice === v.key ? 'bg-primary text-white' : 'bg-slate-800 text-slate-500'}`}
                                                    >
                                                        {previewVoice === v.key ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3 ml-0.5" />}
                                                    </button>
                                                </div>
                                                <div className="text-left">
                                                    <div className={`text-sm font-bold truncate ${voiceKey === v.key ? 'text-text' : 'text-slate-300'}`}>
                                                        {voiceName(v.key)}
                                                    </div>
                                                    <div className={`text-[11px] line-clamp-1 ${voiceKey === v.key ? 'text-primary' : 'text-slate-500'}`}>
                                                        {voiceDesc(v.key)}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                {/* Premium Voices (Expandable) */}
                                <div>
                                    <button 
                                        onClick={() => setShowAllVoices(!showAllVoices)}
                                        className="w-full flex items-center justify-between p-2 text-[10px] font-bold text-slate-500 hover:text-slate-400"
                                    >
                                        <span>Premiumstimmen</span>
                                        <ChevronDown className={`w-3 h-3 transition-transform ${showAllVoices ? 'rotate-180' : ''}`} />
                                    </button>
                                    
                                    {showAllVoices && (
                                        <div className="grid grid-cols-2 gap-2 mt-2 max-h-[400px] overflow-y-auto pr-1 custom-scrollbar">
                                            {sortedVoices
                                                .filter(v => !isStandardVoice(v.key))
                                                .map(v => (
                                                <div
                                                    key={v.key}
                                                    className={`p-2.5 rounded-xl transition-all border-2 cursor-pointer ${voiceKey === v.key
                                                        ? 'border-primary bg-primary/10'
                                                        : 'border-slate-700 bg-slate-800/60 hover:border-slate-600'
                                                        }`}
                                                    onClick={() => setVoiceKey(v.key)}
                                                >
                                                    <div className="flex flex-col gap-2">
                                                        <div className="flex items-center justify-between w-full">
                                                            <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${voiceKey === v.key ? 'bg-primary/20 text-primary' : 'bg-slate-900 text-slate-600'}`}>
                                                                {v.gender === 'female' ? <Venus className="w-3.5 h-3.5" /> :
                                                                    v.gender === 'male' ? <Mars className="w-3.5 h-3.5" /> : <Users className="w-3.5 h-3.5" />}
                                                            </div>
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handlePreviewVoice(v.key); }}
                                                                className={`w-6 h-6 rounded-full flex items-center justify-center transition-all ${previewVoice === v.key ? 'bg-primary text-white' : 'bg-slate-800 text-slate-500'}`}
                                                            >
                                                                {previewVoice === v.key ? <Pause className="w-2.5 h-2.5" /> : <Play className="w-2.5 h-2.5 ml-0.5" />}
                                                            </button>
                                                        </div>
                                                        <div className="text-left">
                                                            <div className={`text-[12px] font-bold truncate ${voiceKey === v.key ? 'text-text' : 'text-slate-300'}`}>
                                                                {voiceName(v.key)}
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Mobile Generate Button (Hidden on Desktop) */}
            <div className="lg:hidden fixed bottom-24 left-0 right-0 flex justify-center z-40 pointer-events-none px-4">
                <div className="pointer-events-auto relative">
                    <div className="absolute -inset-1.5 bg-background/30 backdrop-blur-md rounded-full -z-10 border border-white/5" />
                    <button
                        onClick={handleGenerate}
                        className="btn-primary px-8 py-3.5 text-[17px] font-serif shadow-xl"
                    >
                        <Sparkles className="w-5 h-5 shrink-0" />
                        Neue Geschichte
                    </button>
                </div>
            </div>

            <audio ref={audioRef} className="hidden" />
        </div>
    );
}

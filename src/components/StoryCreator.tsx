import { useState, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { getVoicePreviewUrl, generateHook, fetchPopularity } from '../lib/api';
import { Sparkles, Mic, MicOff, Play, Pause, Venus, Mars, Users, Dices, Loader2, ChevronDown, RefreshCw, Feather } from 'lucide-react';
import { voiceName, voiceDesc, STANDARD_VOICE_KEYS, isStandardVoice } from '../lib/voices';
import { AUTHORS } from '../lib/authors';
import toast from 'react-hot-toast';

const GENRES = [
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
            // Pick a random genre
            const randomGenre = GENRES[Math.floor(Math.random() * GENRES.length)].value;
            // Pick a random author from the full list
            const randomAuthor = AUTHORS[Math.floor(Math.random() * AUTHORS.length)].id;

            // Set UI Defaults
            setGenre(randomGenre);
            setSelectedAuthors([randomAuthor]);
            setTargetMinutes(10);
            setVoiceKey('seraphina');
            setFreeText('Würfel eine fantastische Idee...');

            // Fetch hook from LLM
            const hook = await generateHook(randomGenre, randomAuthor);
            setFreeText(hook);

        } catch (error) {
            console.error("Dice error:", error);
            setFreeText("Fehler beim Würfeln. Bitte nochmal probieren.");
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
        <div className="p-4 sm:p-6 max-w-2xl mx-auto">
            <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary mb-4 shadow-lg shadow-primary/15">
                    <Feather className="w-8 h-8 text-white" />
                </div>
                <h1 className="text-2xl font-bold text-text">Kurzgeschichten-Labor</h1>
                <p className="text-text-muted mt-1 font-mono text-[11px] uppercase tracking-wider">Literatur auf Knopfdruck, exakt nach deinem Maß</p>
            </div>

            {generatorParentId && (
                <div className="mb-8 p-4 bg-accent/20 border-2 border-primary/20 rounded-2xl animate-in slide-in-from-top-4 duration-300">
                    <div className="flex items-center justify-between mb-3 text-primary">
                        <div className="flex items-center gap-2 font-bold text-sm">
                            <RefreshCw className="w-4 h-4" />
                            {generatorRemixType === 'sequel' ? 'Remix: Fortsetzung schreiben' : 'Remix: Geschichte verbessern'}
                        </div>
                        <button 
                            onClick={() => setGeneratorRemix(null, null, null)}
                            className="text-[10px] uppercase font-bold tracking-wider px-2 py-1 bg-surface rounded-lg border border-slate-700 hover:border-primary transition-colors"
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

            <div className="space-y-6">
                {/* Description / Idea */}
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <h2 className="text-sm font-semibold text-slate-300 font-serif">
                            Beschreibe deine Idee
                        </h2>
                        <button
                            onClick={handleDiceClick}
                            disabled={isRolling}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 border border-slate-700 text-slate-400 rounded-lg hover:text-primary hover:border-primary/30 hover:bg-slate-700 transition-all font-semibold text-xs disabled:opacity-50"
                        >
                            {isRolling ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Dices className="w-3.5 h-3.5" />}
                            Inspirieren lassen
                        </button>
                    </div>
                    <div className="relative">
                        <textarea
                            value={freeText}
                            onChange={(e) => setFreeText(e.target.value)}
                            placeholder="z.B. Ein Toaster gewinnt das Bewusstsein und versucht, die Welt zu verstehen. Er begegnet einer alten Kaffeemaschine mit existentialistischen Krisen..."
                            rows={4}
                            className="w-full px-4 py-3 bg-surface border-2 border-slate-800 rounded-xl text-sm focus:outline-none focus:border-primary transition-colors placeholder:text-slate-600 resize-none pr-12 font-serif text-text"
                        />
                        <button
                            onClick={isListening ? handleStopListening : handleStartListening}
                            className={`absolute right-3 top-3 p-2 rounded-lg transition-all ${isListening
                                ? 'bg-red-950 text-red-500'
                                : 'text-slate-500 hover:text-primary'
                                }`}
                            title={isListening ? 'Aufnahme stoppen' : 'Spracheingabe'}
                        >
                            {isListening ? <MicOff className="w-5 h-5 animate-pulse" /> : <Mic className="w-5 h-5" />}
                        </button>
                    </div>
                </div>

                {/* Genre */}
                <div>
                    <div className="mb-2">
                        <h2 className="text-sm font-semibold text-slate-300 font-serif">Genre <span className="font-sans font-normal text-slate-500">(bestimmt Ton & Struktur)</span></h2>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-2">
                        {(showAllGenres ? sortedGenres : sortedGenres.slice(0, BEST_OF_COUNT)).map(g => (
                            <button
                                key={g.value}
                                onClick={() => setGenre(g.value)}
                                className={`p-3 rounded-xl text-left transition-all border-2 ${genre === g.value
                                    ? 'border-primary bg-accent/20 shadow-sm'
                                    : 'border-slate-800 bg-surface text-slate-400 hover:border-slate-700'
                                    }`}
                            >
                                <h4 className={`text-sm font-bold ${genre === g.value ? 'text-primary' : 'text-slate-300'}`}>{g.label}</h4>
                                <div className={`text-xs ${genre === g.value ? 'text-primary/70' : 'text-slate-500'}`}>{g.desc}</div>
                            </button>
                        ))}
                    </div>
                    {!showAllGenres && sortedGenres.length > BEST_OF_COUNT && (
                        <button
                            onClick={() => setShowAllGenres(true)}
                            className="mt-2 w-full py-2 rounded-xl border-2 border-dashed border-slate-800 text-xs text-slate-500 hover:border-slate-700 hover:text-slate-400 transition-all flex items-center justify-center gap-1"
                        >
                            <ChevronDown className="w-3 h-3" />
                            {sortedGenres.length - BEST_OF_COUNT} weitere Genres anzeigen
                        </button>
                    )}
                </div>

                {/* Style */}
                <div>
                    <div className="mb-2">
                        <h2 className="text-sm font-semibold text-slate-300 font-serif">
                            Autoren <span className="font-sans font-normal text-slate-500">(max. 3 auswählen, Stil wird gemixt)</span>
                        </h2>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                        {(showAllAuthors ? sortedAuthors : sortedAuthors.slice(0, BEST_OF_COUNT)).map(s => {
                            const isSelected = selectedAuthors.includes(s.id);
                            const index = selectedAuthors.indexOf(s.id);
                            return (
                                <button
                                    key={s.id}
                                    onClick={() => toggleAuthor(s.id)}
                                    className={`relative p-3 rounded-xl text-left transition-all border-2 ${isSelected
                                        ? 'border-primary bg-accent/20 shadow-sm'
                                        : 'border-slate-800 bg-surface hover:border-slate-700 text-slate-300'
                                        }`}
                                >
                                    {isSelected && (
                                        <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-primary text-white flex items-center justify-center text-[10px] font-bold">
                                            {index + 1}
                                        </div>
                                    )}
                                    <h4 className={`text-sm font-bold pr-6 ${isSelected ? 'text-text' : 'text-slate-300'}`}>{s.name}</h4>
                                    <div className={`text-xs ${isSelected ? 'text-primary' : 'text-slate-500'}`}>{s.desc}</div>
                                </button>
                            );
                        })}
                    </div>
                    {!showAllAuthors && sortedAuthors.length > BEST_OF_COUNT && (
                        <button
                            onClick={() => setShowAllAuthors(true)}
                            className="mt-2 w-full py-2 rounded-xl border-2 border-dashed border-slate-800 text-xs text-slate-500 hover:border-slate-700 hover:text-slate-400 transition-all flex items-center justify-center gap-1"
                        >
                            <ChevronDown className="w-3 h-3" />
                            {sortedAuthors.length - BEST_OF_COUNT} weitere Autoren anzeigen
                        </button>
                    )}
                </div>

                {/* Length */}
                <div>
                    <h2 className="text-sm font-semibold text-slate-300 mb-2 font-serif">Länge</h2>
                    <div className="grid grid-cols-3 gap-2">
                        {LENGTHS.map(l => (
                            <button
                                key={l.value}
                                onClick={() => setTargetMinutes(l.value)}
                                className={`p-3 rounded-xl text-center transition-all border-2 ${targetMinutes === l.value
                                    ? 'border-primary bg-accent/20'
                                    : 'border-slate-800 bg-surface hover:border-slate-700'
                                    }`}
                            >
                                <div className={`text-sm font-bold ${targetMinutes === l.value ? 'text-primary' : 'text-slate-300'}`}>{l.label}</div>
                                <div className={`text-xs ${targetMinutes === l.value ? 'text-primary/70' : 'text-slate-500'}`}>{l.sub}</div>
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Voice Selection */}
            <div className="mt-6">
                <h2 className="text-sm font-semibold text-slate-300 mb-2 font-serif">Stimme</h2>

                {/* --- Standard voices (always visible, pinned) --- */}
                <p className="text-xs font-medium text-slate-500 mb-1.5 tracking-wide uppercase">Standardstimmen</p>
                <div className="grid grid-cols-2 gap-2 mb-4">
                    {voices
                        .filter(v => STANDARD_VOICE_KEYS.includes(v.key))
                        .sort((a, b) => STANDARD_VOICE_KEYS.indexOf(a.key) - STANDARD_VOICE_KEYS.indexOf(b.key))
                        .map(v => (
                        <div
                            key={v.key}
                            className={`p-3 rounded-xl transition-all border-2 cursor-pointer h-full ${voiceKey === v.key
                                ? 'border-primary bg-accent/20 shadow-sm'
                                : 'border-slate-800 bg-surface hover:border-slate-700'
                                }`}
                            onClick={() => setVoiceKey(v.key)}
                        >
                            <div className="flex items-center gap-3 h-full">
                                {/* Icon */}
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${voiceKey === v.key ? 'bg-primary/20 text-primary' : 'bg-slate-900 text-slate-600'}`}>
                                    {v.gender === 'female' ? <Venus className="w-5 h-5" /> :
                                        v.gender === 'male' ? <Mars className="w-5 h-5" /> : <Users className="w-5 h-5" />}
                                </div>

                                {/* Name & Charakter */}
                                <div className="flex-1 min-w-0 text-left">
                                    <div className={`text-sm font-bold truncate font-serif ${voiceKey === v.key ? 'text-text' : 'text-slate-300'}`}>
                                        {voiceName(v.key)}
                                    </div>
                                    <div className={`text-xs ${voiceKey === v.key ? 'text-primary' : 'text-slate-500'}`}>
                                        {voiceDesc(v.key)}
                                    </div>
                                </div>

                                {v.key !== 'none' && (
                                    <button
                                        onClick={(e) => { e.stopPropagation(); handlePreviewVoice(v.key); }}
                                        className={`w-8 h-8 rounded-full flex items-center justify-center transition-all shrink-0 ${previewVoice === v.key
                                            ? 'bg-primary text-white'
                                            : 'bg-slate-800 text-slate-500 hover:bg-slate-700'
                                            }`}
                                    >
                                        {previewVoice === v.key ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 ml-0.5" />}
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>

                {/* --- Premium voices (popularity-sorted, with expansion) --- */}
                <p className="text-xs font-medium text-slate-500 mb-1.5 tracking-wide uppercase">Premiumstimmen</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {(() => {
                        const aiVoices = sortedVoices.filter(v => !isStandardVoice(v.key));
                        return (showAllVoices ? aiVoices : aiVoices.slice(0, BEST_OF_COUNT)).map(v => (
                            <div
                                key={v.key}
                                className={`p-3 rounded-xl transition-all border-2 cursor-pointer h-full ${voiceKey === v.key
                                    ? 'border-primary bg-accent/20 shadow-sm'
                                    : 'border-slate-800 bg-surface hover:border-slate-700'
                                    }`}
                                onClick={() => setVoiceKey(v.key)}
                            >
                                <div className="flex items-center gap-3 h-full">
                                    {/* Icon Left */}
                                    <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${voiceKey === v.key ? 'bg-primary/20 text-primary' : 'bg-slate-900 text-slate-600'}`}>
                                        {v.gender === 'female' ? <Venus className="w-5 h-5" /> :
                                            v.gender === 'male' ? <Mars className="w-5 h-5" /> : <Users className="w-5 h-5" />}
                                    </div>

                                    {/* Name & Charakter */}
                                    <div className="flex-1 min-w-0 text-left">
                                        <div className={`text-sm font-bold truncate font-serif ${voiceKey === v.key ? 'text-text' : 'text-slate-300'}`}>
                                            {voiceName(v.key)}
                                        </div>
                                        <div className={`text-xs ${voiceKey === v.key ? 'text-primary' : 'text-slate-500'}`}>
                                            {voiceDesc(v.key)}
                                        </div>
                                    </div>

                                    {/* Play Right */}
                                    <button
                                        onClick={(e) => { e.stopPropagation(); handlePreviewVoice(v.key); }}
                                        className={`w-8 h-8 rounded-full flex items-center justify-center transition-all shrink-0 ${previewVoice === v.key
                                            ? 'bg-primary text-white'
                                            : 'bg-slate-800 text-slate-500 hover:bg-slate-700'
                                            }`}
                                    >
                                        {previewVoice === v.key ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 ml-0.5" />}
                                    </button>
                                </div>
                            </div>
                        ));
                    })()}
                </div>
                {!showAllVoices && sortedVoices.filter(v => !isStandardVoice(v.key)).length > BEST_OF_COUNT && (
                    <button
                        onClick={() => setShowAllVoices(true)}
                        className="mt-2 w-full py-2 rounded-xl border-2 border-dashed border-slate-800 text-xs text-slate-500 hover:border-slate-700 hover:text-slate-400 transition-all flex items-center justify-center gap-1"
                    >
                        <ChevronDown className="w-3 h-3" />
                        {sortedVoices.filter(v => !isStandardVoice(v.key)).length - BEST_OF_COUNT} weitere Stimmen anzeigen
                    </button>
                )}
                <audio ref={audioRef} className="hidden" />
            </div>

            {/* Sticky Generate Button Container */}
            <div className="fixed bottom-[72px] left-0 right-0 p-4 bg-gradient-to-t from-background/90 to-transparent backdrop-blur-sm z-40 max-w-2xl mx-auto pointer-events-none">
                <div className="pointer-events-auto">
                    <button
                        onClick={handleGenerate}
                        className="btn-primary w-full py-4 text-lg font-serif"
                    >
                        <Sparkles className="w-6 h-6" />
                        Neue Geschichte erschaffen
                    </button>
                </div>
            </div>

            {/* Bottom Spacer to prevent content from being hidden behind sticky button */}
            <div className="h-32" />
        </div>
    );
}

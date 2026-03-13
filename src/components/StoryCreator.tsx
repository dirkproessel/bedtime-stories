import { useState, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { getVoicePreviewUrl, generateHook, fetchPopularity } from '../lib/api';
import { Sparkles, Mic, MicOff, Play, Pause, BookOpen, Venus, Mars, Users, Dices, Loader2, ChevronDown, RefreshCw } from 'lucide-react';
import { voiceName, voiceDesc, STANDARD_VOICE_KEYS, isStandardVoice } from '../lib/voices';
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

const AUTHORS = [
    { id: 'kehlmann', name: 'Daniel Kehlmann', desc: 'Präzise, Geistreich, Verspielt.' },
    { id: 'zeh', name: 'Juli Zeh', desc: 'Analytisch, Kühl, Kritisch.' },
    { id: 'fitzek', name: 'Sebastian Fitzek', desc: 'Atemlos, Rasant, Düster.' },
    { id: 'kracht', name: 'Christian Kracht', desc: 'Snobistisch, Dekadent, Distanziert.' },
    { id: 'kafka', name: 'Franz Kafka', desc: 'Surreal, Beklemmend, Trocken.' },
    { id: 'jaud', name: 'Tommy Jaud', desc: 'Lustig, Hektisch, Peinlich.' },
    { id: 'regener', name: 'Sven Regener', desc: 'Lakonisch, Echt, Schnodderig.' },
    { id: 'strunk', name: 'Heinz Strunk', desc: 'Grotesk, Erbarmungslos, Schräg.' },
    { id: 'kling', name: 'Marc-Uwe Kling', desc: 'Schlagfertig, Logisch, Trocken.' },
    { id: 'stuckrad_barre', name: 'Benjamin v. Stuckrad-Barre', desc: 'Nervös, Pop-affin, Hyper.' },
    { id: 'evers', name: 'Horst Evers', desc: 'Absurd, Gemütlich, Skurril.' },
    { id: 'loriot', name: 'Loriot', desc: 'Bürgerlich, Präzise, Absurd.' },
    { id: 'funke', name: 'Cornelia Funke', desc: 'Magisch, Bildstark, Abenteuerlich.' },
    { id: 'pantermueller', name: 'Alice Pantermüller', desc: 'Rotzig, Frech, Chaotisch.' },
    { id: 'auer', name: 'Margit Auer', desc: 'Geborgen, Geheimnisvoll, Empathisch.' },
    { id: 'pratchett', name: 'Terry Pratchett', desc: 'Scharfsinnig, Satirisch, Trocken.' },
    { id: 'adams', name: 'Douglas Adams', desc: 'Absurd, Lakonisch, Kosmisch.' },
    { id: 'kinney', name: 'Jeff Kinney', desc: 'Pubertär, Ironisch, Authentisch.' },
    { id: 'kaestner', name: 'Erich Kästner', desc: 'Ironisch, Klar, Herzlich.' },
    { id: 'lindgren', name: 'Astrid Lindgren', desc: 'Herzlich, Mutig, Kindlich-weise.' },
    { id: 'dahl', name: 'Roald Dahl', desc: 'Skurril, Drastisch, Respektlos.' },
    { id: 'christie', name: 'Agatha Christie', desc: 'Sachlich, Analytisch, Rätselhaft.' },
    { id: 'king', name: 'Stephen King', desc: 'Detailreich, Volksnah, Unheimlich.' },
    { id: 'hemingway', name: 'Ernest Hemingway', desc: 'Karg, Trocken, Präzise.' },
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
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 mb-4 shadow-lg shadow-indigo-500/25">
                    <BookOpen className="w-8 h-8 text-white" />
                </div>
                <h1 className="text-2xl font-bold text-slate-900">Kurzgeschichten-Labor</h1>
                <p className="text-slate-500 mt-1">Literatur auf Knopfdruck, exakt nach deinem Maß</p>
            </div>

            {generatorParentId && (
                <div className="mb-8 p-4 bg-indigo-50 border-2 border-indigo-100 rounded-2xl animate-in slide-in-from-top-4 duration-300">
                    <div className="flex items-center justify-between mb-3 text-indigo-700">
                        <div className="flex items-center gap-2 font-bold text-sm">
                            <RefreshCw className="w-4 h-4" />
                            {generatorRemixType === 'sequel' ? 'Remix: Fortsetzung schreiben' : 'Remix: Geschichte verbessern'}
                        </div>
                        <button 
                            onClick={() => setGeneratorRemix(null, null, null)}
                            className="text-[10px] uppercase font-bold tracking-wider px-2 py-1 bg-white rounded-lg border border-indigo-200 hover:border-indigo-400 transition-colors"
                        >
                            Abbrechen
                        </button>
                    </div>
                    {generatorContext && (
                        <div className="bg-white/60 p-3 rounded-xl border border-indigo-100/50">
                            <h4 className="font-bold text-xs text-slate-700 truncate">{generatorContext.title}</h4>
                            <p className="text-[10px] text-slate-500 line-clamp-2 mt-0.5 leading-relaxed">{generatorContext.synopsis}</p>
                        </div>
                    )}
                </div>
            )}

            <div className="space-y-6">
                {/* Description / Idea */}
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <label className="block text-sm font-semibold text-slate-700">
                            Beschreibe deine Idee
                        </label>
                        <button
                            onClick={handleDiceClick}
                            disabled={isRolling}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-amber-100 to-orange-100 text-amber-800 rounded-lg hover:from-amber-200 hover:to-orange-200 transition-all font-semibold text-xs shadow-sm shadow-orange-100/50 opacity-90 hover:opacity-100 disabled:opacity-50"
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
                            className="w-full px-4 py-3 bg-white border-2 border-slate-100 rounded-xl text-sm focus:outline-none focus:border-indigo-400 transition-colors placeholder:text-slate-300 resize-none pr-12"
                        />
                        <button
                            onClick={isListening ? handleStopListening : handleStartListening}
                            className={`absolute right-3 top-3 p-2 rounded-lg transition-all ${isListening
                                ? 'bg-red-50 text-red-600'
                                : 'text-slate-400 hover:text-indigo-500'
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
                        <label className="block text-sm font-semibold text-slate-700">Genre <span className="font-normal text-slate-400">(bestimmt Ton & Struktur)</span></label>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-2">
                        {(showAllGenres ? sortedGenres : sortedGenres.slice(0, BEST_OF_COUNT)).map(g => (
                            <button
                                key={g.value}
                                onClick={() => setGenre(g.value)}
                                className={`p-3 rounded-xl text-left transition-all border-2 ${genre === g.value
                                    ? 'border-indigo-500 bg-indigo-50 shadow-sm'
                                    : 'border-slate-100 bg-white text-slate-600 hover:border-slate-200'
                                    }`}
                            >
                                <div className={`text-sm font-bold ${genre === g.value ? 'text-indigo-700' : 'text-slate-700'}`}>{g.label}</div>
                                <div className={`text-xs ${genre === g.value ? 'text-indigo-500' : 'text-slate-400'}`}>{g.desc}</div>
                            </button>
                        ))}
                    </div>
                    {!showAllGenres && sortedGenres.length > BEST_OF_COUNT && (
                        <button
                            onClick={() => setShowAllGenres(true)}
                            className="mt-2 w-full py-2 rounded-xl border-2 border-dashed border-slate-200 text-xs text-slate-400 hover:border-slate-300 hover:text-slate-500 transition-all flex items-center justify-center gap-1"
                        >
                            <ChevronDown className="w-3 h-3" />
                            {sortedGenres.length - BEST_OF_COUNT} weitere Genres anzeigen
                        </button>
                    )}
                </div>

                {/* Style */}
                <div>
                    <div className="mb-2">
                        <label className="block text-sm font-semibold text-slate-700">
                            Autoren <span className="font-normal text-slate-400">(max. 3 auswählen, Stil wird gemixt)</span>
                        </label>
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
                                        ? 'border-indigo-500 bg-indigo-50 shadow-sm'
                                        : 'border-slate-100 bg-white hover:border-slate-200'
                                        }`}
                                >
                                    {isSelected && (
                                        <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-indigo-500 text-white flex items-center justify-center text-[10px] font-bold">
                                            {index + 1}
                                        </div>
                                    )}
                                    <div className={`text-sm font-bold pr-6 ${isSelected ? 'text-indigo-700' : 'text-slate-700'}`}>{s.name}</div>
                                    <div className={`text-xs ${isSelected ? 'text-indigo-500' : 'text-slate-400'}`}>{s.desc}</div>
                                </button>
                            );
                        })}
                    </div>
                    {!showAllAuthors && sortedAuthors.length > BEST_OF_COUNT && (
                        <button
                            onClick={() => setShowAllAuthors(true)}
                            className="mt-2 w-full py-2 rounded-xl border-2 border-dashed border-slate-200 text-xs text-slate-400 hover:border-slate-300 hover:text-slate-500 transition-all flex items-center justify-center gap-1"
                        >
                            <ChevronDown className="w-3 h-3" />
                            {sortedAuthors.length - BEST_OF_COUNT} weitere Autoren anzeigen
                        </button>
                    )}
                </div>

                {/* Length */}
                <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-2">Länge</label>
                    <div className="grid grid-cols-3 gap-2">
                        {LENGTHS.map(l => (
                            <button
                                key={l.value}
                                onClick={() => setTargetMinutes(l.value)}
                                className={`p-3 rounded-xl text-center transition-all border-2 ${targetMinutes === l.value
                                    ? 'border-indigo-500 bg-indigo-50'
                                    : 'border-slate-100 bg-white hover:border-slate-200'
                                    }`}
                            >
                                <div className={`text-sm font-bold ${targetMinutes === l.value ? 'text-indigo-700' : 'text-slate-700'}`}>{l.label}</div>
                                <div className={`text-xs ${targetMinutes === l.value ? 'text-indigo-500' : 'text-slate-400'}`}>{l.sub}</div>
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Voice Selection */}
            <div className="mt-6">
                <label className="block text-sm font-semibold text-slate-700 mb-2">Stimme</label>

                {/* --- Standard voices (always visible, pinned) --- */}
                <p className="text-xs font-medium text-slate-400 mb-1.5 tracking-wide uppercase">Standardstimmen</p>
                <div className="grid grid-cols-2 gap-2 mb-4">
                    {voices
                        .filter(v => STANDARD_VOICE_KEYS.includes(v.key))
                        .sort((a, b) => STANDARD_VOICE_KEYS.indexOf(a.key) - STANDARD_VOICE_KEYS.indexOf(b.key))
                        .map(v => (
                        <div
                            key={v.key}
                            className={`p-3 rounded-xl transition-all border-2 cursor-pointer ${voiceKey === v.key
                                ? 'border-indigo-500 bg-indigo-50 shadow-sm'
                                : 'border-slate-100 bg-white hover:border-slate-200'
                                }`}
                            onClick={() => setVoiceKey(v.key)}
                        >
                            <div className="flex items-center gap-3">
                                {/* Icon */}
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${voiceKey === v.key ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-50 text-slate-400'}`}>
                                    {v.gender === 'female' ? <Venus className="w-5 h-5" /> :
                                        v.gender === 'male' ? <Mars className="w-5 h-5" /> : <Users className="w-5 h-5" />}
                                </div>

                                {/* Name & Charakter */}
                                <div className="flex-1 min-w-0 text-left">
                                    <div className={`text-sm font-bold truncate ${voiceKey === v.key ? 'text-indigo-700' : 'text-slate-700'}`}>
                                        {voiceName(v.key)}
                                    </div>
                                    <div className={`text-xs ${voiceKey === v.key ? 'text-indigo-500' : 'text-slate-400'}`}>
                                        {voiceDesc(v.key)}
                                    </div>
                                </div>

                                {v.key !== 'none' && (
                                    <button
                                        onClick={(e) => { e.stopPropagation(); handlePreviewVoice(v.key); }}
                                        className={`w-8 h-8 rounded-full flex items-center justify-center transition-all shrink-0 ${previewVoice === v.key
                                            ? 'bg-indigo-500 text-white'
                                            : 'bg-slate-100 text-slate-400 hover:bg-slate-200'
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
                <p className="text-xs font-medium text-slate-400 mb-1.5 tracking-wide uppercase">Premiumstimmen</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {(() => {
                        const aiVoices = sortedVoices.filter(v => !isStandardVoice(v.key));
                        return (showAllVoices ? aiVoices : aiVoices.slice(0, BEST_OF_COUNT)).map(v => (
                            <div
                                key={v.key}
                                className={`p-3 rounded-xl transition-all border-2 cursor-pointer ${voiceKey === v.key
                                    ? 'border-indigo-500 bg-indigo-50 shadow-sm'
                                    : 'border-slate-100 bg-white hover:border-slate-200'
                                    }`}
                                onClick={() => setVoiceKey(v.key)}
                            >
                                <div className="flex items-center gap-3">
                                    {/* Icon Left */}
                                    <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${voiceKey === v.key ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-50 text-slate-400'}`}>
                                        {v.gender === 'female' ? <Venus className="w-5 h-5" /> :
                                            v.gender === 'male' ? <Mars className="w-5 h-5" /> : <Users className="w-5 h-5" />}
                                    </div>

                                    {/* Name & Charakter */}
                                    <div className="flex-1 min-w-0 text-left">
                                        <div className={`text-sm font-bold truncate ${voiceKey === v.key ? 'text-indigo-700' : 'text-slate-700'}`}>
                                            {voiceName(v.key)}
                                        </div>
                                        <div className={`text-xs ${voiceKey === v.key ? 'text-indigo-500' : 'text-slate-400'}`}>
                                            {voiceDesc(v.key)}
                                        </div>
                                    </div>

                                    {/* Play Right */}
                                    <button
                                        onClick={(e) => { e.stopPropagation(); handlePreviewVoice(v.key); }}
                                        className={`w-8 h-8 rounded-full flex items-center justify-center transition-all shrink-0 ${previewVoice === v.key
                                            ? 'bg-indigo-500 text-white'
                                            : 'bg-slate-100 text-slate-400 hover:bg-slate-200'
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
                        className="mt-2 w-full py-2 rounded-xl border-2 border-dashed border-slate-200 text-xs text-slate-400 hover:border-slate-300 hover:text-slate-500 transition-all flex items-center justify-center gap-1"
                    >
                        <ChevronDown className="w-3 h-3" />
                        {sortedVoices.filter(v => !isStandardVoice(v.key)).length - BEST_OF_COUNT} weitere Stimmen anzeigen
                    </button>
                )}
                <audio ref={audioRef} className="hidden" />
            </div>

            {/* Sticky Generate Button Container */}
            <div className="fixed bottom-[72px] left-0 right-0 p-4 bg-gradient-to-t from-slate-50/90 to-transparent backdrop-blur-sm z-40 max-w-2xl mx-auto pointer-events-none">
                <div className="pointer-events-auto">
                    <button
                        onClick={handleGenerate}
                        className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-4 rounded-xl font-bold text-lg shadow-lg shadow-indigo-200 hover:shadow-xl hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2"
                    >
                        <Sparkles className="w-6 h-6" />
                        Geschichte jetzt schreiben
                    </button>
                </div>
            </div>

            {/* Bottom Spacer to prevent content from being hidden behind sticky button */}
            <div className="h-32" />
        </div>
    );
}

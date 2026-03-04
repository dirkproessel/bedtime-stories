import { useState, useRef } from 'react';
import { useStore } from '../store/useStore';
import { getVoicePreviewUrl, generateHook } from '../lib/api';
import { Sparkles, Mic, MicOff, Play, Pause, BookOpen, Venus, Mars, Users, Dices, Loader2 } from 'lucide-react';

const GENRES = [
    { value: 'Krimi', label: 'Krimi', desc: 'Indizien, Verdächtige, falsche Fährten' },
    { value: 'Abenteuer', label: 'Abenteuer', desc: 'Aufbruch, Hindernisse, Heldenreise' },
    { value: 'Science-Fiction', label: 'Science-Fiction', desc: 'Zukunfts-Technik, fremde Welten' },
    { value: 'Märchen', label: 'Märchen', desc: 'Magische Wesen, Wandlung, Alltagsmagie' },
    { value: 'Komödie', label: 'Komödie', desc: 'Situationskomik, Verwechslungen' },
    { value: 'Thriller', label: 'Thriller', desc: 'Countdown, hohe Spannung, verborgene Gefahr' },
    { value: 'Drama', label: 'Drama', desc: 'Tiefe Dialoge, Fokus auf Freundschaft' },
    { value: 'Grusel', label: 'Grusel', desc: 'Schatten, alte Geheimnisse, Gänsehaut' },
];

const AUTHORS = [
    { id: 'kehlmann', name: 'Daniel Kehlmann', desc: 'Präzise, Geistreich, Verspielt.', group: 'Erwachsene' },
    { id: 'zeh', name: 'Juli Zeh', desc: 'Analytisch, Kühl, Kritisch.', group: 'Erwachsene' },
    { id: 'fitzek', name: 'Sebastian Fitzek', desc: 'Atemlos, Rasant, Düster.', group: 'Erwachsene' },
    // { id: 'sueskind', name: 'Patrick Süskind', desc: 'Sinnlich, Historisch, Exakt.', group: 'Erwachsene' },
    { id: 'kracht', name: 'Christian Kracht', desc: 'Snobistisch, Dekadent, Distanziert.', group: 'Erwachsene' },
    // { id: 'bachmann', name: 'Ingeborg Bachmann', desc: 'Metaphorisch, Melancholisch, Intensiv.', group: 'Erwachsene' },
    { id: 'kafka', name: 'Franz Kafka', desc: 'Surreal, Beklemmend, Trocken.', group: 'Erwachsene' },
    // { id: 'borchert', name: 'Wolfgang Borchert', desc: 'Hart, Kalt, Existenziell.', group: 'Erwachsene' },
    { id: 'jaud', name: 'Tommy Jaud', desc: 'Lustig, Hektisch, Peinlich.', group: 'Erwachsene' },
    { id: 'regener', name: 'Sven Regener', desc: 'Lakonisch, Echt, Schnodderig', group: 'Erwachsene' },
    { id: 'strunk', name: 'Heinz Strunk', desc: 'Grotesk, Erbarmungslos, Schräg', group: 'Erwachsene' },
    { id: 'kling', name: 'Marc-Uwe Kling', desc: 'Schlagfertig, Logisch, Trocken', group: 'Erwachsene' },
    { id: 'stuckrad_barre', name: 'Benjamin v. Stuckrad-Barre', desc: 'Nervös, Pop-affin, Hyper', group: 'Erwachsene' },
    { id: 'evers', name: 'Horst Evers', desc: 'Absurd, Gemütlich, Skurril', group: 'Erwachsene' },
    { id: 'loriot', name: 'Loriot', desc: 'Bürgerlich, Präzise, Absurd', group: 'Erwachsene' },
    { id: 'funke', name: 'Cornelia Funke', desc: 'Magisch, Bildstark, Abenteuerlich.', group: 'Kinder' },
    { id: 'pantermueller', name: 'Alice Pantermüller', desc: 'Rotzig, Frech, Chaotisch.', group: 'Kinder' },
    { id: 'auer', name: 'Margit Auer', desc: 'Geborgen, Geheimnisvoll, Empathisch.', group: 'Kinder' },
];

const LENGTHS = [
    { value: 10, label: '~10 Min', sub: '2 Kapitel' },
    { value: 15, label: '~15 Min', sub: '3 Kapitel' },
    { value: 20, label: '~20 Min', sub: '4 Kapitel' },
];

export default function StoryCreator() {
    const { voices, startGeneration } = useStore();

    // Selection state
    const [genre, setGenre] = useState('Abenteuer');
    const [selectedAuthors, setSelectedAuthors] = useState<string[]>([]);

    const toggleAuthor = (id: string) => {
        setSelectedAuthors(prev => {
            if (prev.includes(id)) return prev.filter(x => x !== id);
            if (prev.length >= 3) return prev;
            return [...prev, id];
        });
    };
    const [targetMinutes, setTargetMinutes] = useState(15);
    const [voiceKey, setVoiceKey] = useState('seraphina');

    // Input state
    const [freeText, setFreeText] = useState('');
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
            // Pick a random adult author (kids authors are less likely to give the surreal vibe)
            const adultAuthors = AUTHORS.filter(a => a.group === 'Erwachsene');
            const randomAuthor = adultAuthors[Math.floor(Math.random() * adultAuthors.length)].id;

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
        const idea = freeText.trim() || 'Überrasche mich mit einer wunderbaren Geschichte.';

        const selectedGenre = GENRES.find(g => g.value === genre);
        // Create the system prompt for the LLM
        const systemPrompt = `Kurzgeschichte im Genre ${selectedGenre?.label || genre}\n\nIdee: ${freeText}`;

        // Start generation - use the idea as the prompt for metadata display
        startGeneration({
            prompt: idea, // This will be stored and shown as "Idee"
            system_prompt: systemPrompt,
            genre: selectedGenre?.label || genre,
            style: selectedAuthors.length > 0 ? selectedAuthors.join(',') : 'kehlmann',
            target_minutes: targetMinutes,
            voice_key: voiceKey
        } as any);
    };

    return (
        <div className="p-4 sm:p-6 max-w-2xl mx-auto">
            <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 mb-4 shadow-lg shadow-indigo-500/25">
                    <BookOpen className="w-8 h-8 text-white" />
                </div>
                <h1 className="text-2xl font-bold text-slate-900">Kurzgeschichten-Labor</h1>
                <p className="text-slate-500 mt-1">Anspruchsvolle Literatur für Groß und Klein</p>
            </div>

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
                    <label className="block text-sm font-semibold text-slate-700 mb-2">Genre</label>
                    <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-2">
                        {GENRES.map(g => (
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
                </div>

                {/* Style */}
                <div>
                    <div className="flex justify-between items-end mb-2">
                        <label className="block text-sm font-semibold text-slate-700">Autoren (max. 3 mixen)</label>
                        <div className="text-xs font-medium text-slate-500">
                            {selectedAuthors.length === 0 ? "Stil wird gemixt" : `${selectedAuthors.length} von 3 gewählt`}
                        </div>
                    </div>

                    <div className="space-y-4">
                        {/* Erwachsene */}
                        <div>
                            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Für Erwachsene</div>
                            <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                                {AUTHORS.filter(a => a.group === 'Erwachsene').map(s => {
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
                        </div>

                        {/* Kinder */}
                        <div>
                            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Für Kinder</div>
                            <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                                {AUTHORS.filter(a => a.group === 'Kinder').map(s => {
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
                        </div>
                    </div>
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
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {voices.map(v => (
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

                                {/* Name & Quality Center */}
                                <div className="flex-1 min-w-0 text-left">
                                    <div className={`text-sm font-bold truncate capitalize ${voiceKey === v.key ? 'text-indigo-700' : 'text-slate-700'}`}>
                                        {v.name}
                                    </div>
                                    <div className={`text-xs ${voiceKey === v.key ? 'text-indigo-500' : 'text-slate-400'}`}>
                                        {v.engine === 'gemini' || v.engine === 'openai' ? 'Premium ($)' : 'Standard'}
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
                    ))}
                </div>
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

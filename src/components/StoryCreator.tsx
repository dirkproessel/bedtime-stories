import { useState, useRef } from 'react';
import { useStore } from '../store/useStore';
import { getVoicePreviewUrl, type GenerationStatus } from '../lib/api';
import { Sparkles, Mic, MicOff, Play, Pause, BookOpen, Wand2, MessageSquareText } from 'lucide-react';

const THEMES = [
    { value: 'abenteuer', label: '🗺️ Abenteuer' },
    { value: 'fantasie', label: '🧚 Fantasie' },
    { value: 'tiere', label: '🐻 Tiere' },
    { value: 'weltraum', label: '🚀 Weltraum' },
    { value: 'unterwasser', label: '🐠 Unterwasser' },
    { value: 'wald', label: '🌲 Wald & Natur' },
    { value: 'freundschaft', label: '🤝 Freundschaft' },
    { value: 'magie', label: '✨ Magie & Zauberei' },
];

const STYLES = [
    { value: 'märchenhaft', label: '🏰 Märchenhaft' },
    { value: 'lustig', label: '😄 Lustig' },
    { value: 'spannend', label: '😮 Spannend' },
    { value: 'beruhigend', label: '😴 Beruhigend' },
    { value: 'poetisch', label: '🌸 Poetisch' },
];

const LENGTHS = [
    { value: 10, label: '~10 Min', sub: 'Kurz' },
    { value: 20, label: '~20 Min', sub: 'Mittel' },
    { value: 30, label: '~30 Min', sub: 'Lang' },
];

export default function StoryCreator() {
    const { voices, startGeneration, startFreeGeneration, isGenerating, generationStatus } = useStore();
    const [mode, setMode] = useState<'guided' | 'free'>('guided');

    // Guided mode state
    const [theme, setTheme] = useState('abenteuer');
    const [style, setStyle] = useState('märchenhaft');
    const [characters, setCharacters] = useState('');
    const [targetMinutes, setTargetMinutes] = useState(20);
    const [voiceKey, setVoiceKey] = useState('katja');

    // Free mode state
    const [freeText, setFreeText] = useState('');

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

    const handleGenerate = () => {
        if (mode === 'guided') {
            const selectedTheme = THEMES.find(t => t.value === theme);
            const prompt = `${selectedTheme?.label || theme}${characters ? ` mit den Charakteren: ${characters}` : ''}`;
            startGeneration({
                prompt,
                style,
                characters: characters ? characters.split(',').map(c => c.trim()) : undefined,
                target_minutes: targetMinutes,
                voice_key: voiceKey,
            });
        } else {
            if (!freeText.trim()) return;
            startFreeGeneration(freeText.trim(), voiceKey, targetMinutes);
        }
    };

    if (isGenerating && generationStatus) {
        return <GenerationProgress status={generationStatus} />;
    }

    return (
        <div className="p-4 sm:p-6 max-w-2xl mx-auto">
            <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 mb-4 shadow-lg shadow-indigo-500/25">
                    <BookOpen className="w-8 h-8 text-white" />
                </div>
                <h1 className="text-2xl font-bold text-slate-900">Neue Geschichte</h1>
                <p className="text-slate-500 mt-1">Erstelle eine einzigartige Gute-Nacht-Geschichte</p>
            </div>

            {/* Mode Toggle */}
            <div className="flex bg-slate-100 rounded-xl p-1 mb-6">
                <button
                    onClick={() => setMode('guided')}
                    className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all ${mode === 'guided'
                        ? 'bg-white text-slate-900 shadow-sm'
                        : 'text-slate-500 hover:text-slate-700'
                        }`}
                >
                    <Wand2 className="w-4 h-4" />
                    Geführt
                </button>
                <button
                    onClick={() => setMode('free')}
                    className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all ${mode === 'free'
                        ? 'bg-white text-slate-900 shadow-sm'
                        : 'text-slate-500 hover:text-slate-700'
                        }`}
                >
                    <MessageSquareText className="w-4 h-4" />
                    Freie Eingabe
                </button>
            </div>

            {mode === 'guided' ? (
                <div className="space-y-6">
                    {/* Theme */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">Thema</label>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                            {THEMES.map(t => (
                                <button
                                    key={t.value}
                                    onClick={() => setTheme(t.value)}
                                    className={`p-3 rounded-xl text-sm font-medium transition-all border-2 ${theme === t.value
                                        ? 'border-indigo-500 bg-indigo-50 text-indigo-700 shadow-sm'
                                        : 'border-slate-100 bg-white text-slate-600 hover:border-slate-200'
                                        }`}
                                >
                                    {t.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Style */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">Stil</label>
                        <div className="flex flex-wrap gap-2">
                            {STYLES.map(s => (
                                <button
                                    key={s.value}
                                    onClick={() => setStyle(s.value)}
                                    className={`px-4 py-2 rounded-full text-sm font-medium transition-all border-2 ${style === s.value
                                        ? 'border-purple-500 bg-purple-50 text-purple-700'
                                        : 'border-slate-100 bg-white text-slate-600 hover:border-slate-200'
                                        }`}
                                >
                                    {s.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Characters */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Charaktere <span className="font-normal text-slate-400">(optional)</span>
                        </label>
                        <input
                            type="text"
                            value={characters}
                            onChange={(e) => setCharacters(e.target.value)}
                            placeholder="z.B. Luna die Katze, Max der Bär"
                            className="w-full px-4 py-3 bg-white border-2 border-slate-100 rounded-xl text-sm focus:outline-none focus:border-indigo-400 transition-colors placeholder:text-slate-300"
                        />
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
            ) : (
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Beschreibe deine Geschichte
                        </label>
                        <textarea
                            value={freeText}
                            onChange={(e) => setFreeText(e.target.value)}
                            placeholder="z.B. Eine Geschichte über einen kleinen Drachen, der lernt zu fliegen und dabei neue Freunde findet..."
                            rows={5}
                            className="w-full px-4 py-3 bg-white border-2 border-slate-100 rounded-xl text-sm focus:outline-none focus:border-indigo-400 transition-colors placeholder:text-slate-300 resize-none"
                        />
                    </div>
                    <button
                        onClick={isListening ? handleStopListening : handleStartListening}
                        className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${isListening
                            ? 'bg-red-50 text-red-600 border-2 border-red-200'
                            : 'bg-slate-50 text-slate-600 border-2 border-slate-100 hover:border-slate-200'
                            }`}
                    >
                        {isListening ? <MicOff className="w-4 h-4 animate-pulse" /> : <Mic className="w-4 h-4" />}
                        {isListening ? 'Aufnahme stoppen' : 'Spracheingabe'}
                    </button>

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
            )}

            {/* Voice Selection */}
            <div className="mt-6">
                <label className="block text-sm font-semibold text-slate-700 mb-2">Stimme</label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {voices.map(v => (
                        <div
                            key={v.key}
                            className={`relative p-3 rounded-xl transition-all border-2 cursor-pointer ${voiceKey === v.key
                                ? 'border-indigo-500 bg-indigo-50'
                                : 'border-slate-100 bg-white hover:border-slate-200'
                                }`}
                            onClick={() => setVoiceKey(v.key)}
                        >
                            <div className="flex items-center justify-between">
                                <div>
                                    <div className={`text-sm font-bold ${voiceKey === v.key ? 'text-indigo-700' : 'text-slate-700'}`}>{v.name}</div>
                                    <div className={`text-xs ${voiceKey === v.key ? 'text-indigo-500' : 'text-slate-400'}`}>
                                        {v.gender === 'female' ? '♀ Weiblich' : '♂ Männlich'}
                                    </div>
                                </div>
                                <button
                                    onClick={(e) => { e.stopPropagation(); handlePreviewVoice(v.key); }}
                                    className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${previewVoice === v.key
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

            {/* Generate Button */}
            <button
                onClick={handleGenerate}
                disabled={isGenerating || (mode === 'free' && !freeText.trim())}
                className="mt-8 w-full flex items-center justify-center gap-2 py-4 bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold rounded-2xl shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            >
                <Sparkles className="w-5 h-5" />
                Geschichte generieren
            </button>
        </div>
    );
}

function GenerationProgress({ status }: { status: GenerationStatus }) {
    const stages = [
        { key: 'outline', label: 'Gliederung erstellen' },
        { key: 'chapter', label: 'Geschichte schreiben' },
        { key: 'generating_text', label: 'Text generieren' },
        { key: 'generating_audio', label: 'Audio erstellen' },
        { key: 'tts', label: 'Vertonung' },
        { key: 'processing', label: 'Zusammenfügen' },
        { key: 'done', label: 'Fertig!' },
    ];

    const currentIndex = stages.findIndex(s => s.key === status.status);
    const progress = status.status === 'done' ? 100 : Math.max(10, ((currentIndex + 1) / stages.length) * 100);

    return (
        <div className="p-6 max-w-md mx-auto flex flex-col items-center justify-center min-h-[60vh]">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-6 shadow-lg shadow-indigo-500/25 animate-pulse">
                <Sparkles className="w-10 h-10 text-white" />
            </div>

            {status.title && (
                <h2 className="text-lg font-bold text-slate-900 mb-2 text-center">
                    {status.title}
                </h2>
            )}

            <p className="text-sm text-slate-500 mb-6 text-center">{status.progress}</p>

            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                <div
                    className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-700 ease-out"
                    style={{ width: `${progress}%` }}
                />
            </div>

            {status.status === 'error' && (
                <div className="mt-4 p-3 bg-red-50 text-red-600 rounded-xl text-sm">
                    {status.progress}
                </div>
            )}
        </div>
    );
}

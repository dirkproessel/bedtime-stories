import { useState, useRef } from 'react';
import { useStore } from '../store/useStore';
import { getVoicePreviewUrl, type GenerationStatus } from '../lib/api';
import { Sparkles, Mic, MicOff, Play, Pause, BookOpen, Venus, Mars, Users } from 'lucide-react';

const GENRES = [
    { value: 'Sci-Fi', label: 'Sci-Fi' },
    { value: 'Fantasy', label: 'Fantasy' },
    { value: 'Krimi', label: 'Krimi' },
    { value: 'Abenteuer', label: 'Abenteuer' },
    { value: 'Realismus', label: 'Realismus' },
    { value: 'Grusel', label: 'Grusel' },
    { value: 'Dystopie', label: 'Dystopie' },
    { value: 'Satire', label: 'Satire' },
];

const STYLES = [
    { value: 'Douglas Adams', label: 'Douglas Adams', desc: 'Absurd, ironisch, kosmisch' },
    { value: 'Ernest Hemingway', label: 'Ernest Hemingway', desc: 'Minimalistisch, knapp, präzise' },
    { value: 'Edgar Allan Poe', label: 'Edgar Allan Poe', desc: 'Gothic, düster, schaurig' },
    { value: 'Virginia Woolf', label: 'Virginia Woolf', desc: 'Poetisch, bildreich, fließend' },
    { value: 'Charles Bukowski', label: 'Charles Bukowski', desc: 'Sarkastisch, bissig, ehrlich' },
    { value: 'Franz Kafka', label: 'Franz Kafka', desc: 'Surreal, traumhaft, rätselhaft' },
    { value: 'Hunter S. Thompson', label: 'Hunter S. Thompson', desc: 'Gonzo, wild, subjektiv' },
    { value: 'Roald Dahl', label: 'Roald Dahl', desc: 'Makaber, witzig, unvorhersehbar' },
];

const LENGTHS = [
    { value: 10, label: '~10 Min', sub: 'Kurz' },
    { value: 20, label: '~20 Min', sub: 'Mittel' },
    { value: 30, label: '~30 Min', sub: 'Lang' },
];

export default function StoryCreator() {
    const { voices, startGeneration, isGenerating, generationStatus } = useStore();

    // Selection state
    const [genre, setGenre] = useState('Realismus');
    const [style, setStyle] = useState('Douglas Adams');
    const [targetMinutes, setTargetMinutes] = useState(20);
    const [voiceKey, setVoiceKey] = useState('seraphina');

    // Input state
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
        if (!freeText.trim()) return;

        const selectedGenre = GENRES.find(g => g.value === genre);
        const prompt = `Kurzgeschichte im Genre ${selectedGenre?.label || genre}\n\nIdee: ${freeText}`;

        startGeneration({
            prompt,
            genre,
            style,
            target_minutes: targetMinutes,
            voice_key: voiceKey,
        });
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
                <h1 className="text-2xl font-bold text-slate-900">Kurzgeschichten-Labor</h1>
                <p className="text-slate-500 mt-1">Anspruchsvolle Literatur für Groß und Klein</p>
            </div>

            <div className="space-y-6">
                {/* Description / Idea */}
                <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-2">
                        Beschreibe deine Idee
                    </label>
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
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                        {GENRES.map(g => (
                            <button
                                key={g.value}
                                onClick={() => setGenre(g.value)}
                                className={`p-3 rounded-xl text-sm font-medium transition-all border-2 ${genre === g.value
                                    ? 'border-indigo-500 bg-indigo-50 text-indigo-700 shadow-sm'
                                    : 'border-slate-100 bg-white text-slate-600 hover:border-slate-200'
                                    }`}
                            >
                                {g.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Style */}
                <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-2">Stil</label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {STYLES.map(s => (
                            <button
                                key={s.value}
                                onClick={() => setStyle(s.value)}
                                className={`p-3 rounded-xl text-left transition-all border-2 ${style === s.value
                                    ? 'border-purple-500 bg-purple-50'
                                    : 'border-slate-100 bg-white hover:border-slate-200'
                                    }`}
                            >
                                <div className={`text-sm font-bold ${style === s.value ? 'text-purple-700' : 'text-slate-700'}`}>{s.label}</div>
                                <div className={`text-xs ${style === s.value ? 'text-purple-500' : 'text-slate-400'}`}>{s.desc}</div>
                            </button>
                        ))}
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
                                    <div className={`text-sm font-bold truncate ${voiceKey === v.key ? 'text-indigo-700' : 'text-slate-700'}`}>
                                        {v.name}
                                    </div>
                                    <div className={`text-[10px] font-medium ${v.engine === 'openai' ? 'text-purple-600' :
                                        v.engine === 'google' ? 'text-blue-600' : 'text-slate-400'
                                        }`}>
                                        {v.engine === 'openai' ? 'Premium ($)' :
                                            v.engine === 'google' ? 'Standard+' : 'Standard'}
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

            {/* Generate Button */}
            <button
                onClick={handleGenerate}
                disabled={isGenerating || !freeText.trim()}
                className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-4 rounded-xl font-bold text-lg shadow-lg shadow-indigo-200 hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:translate-y-0 flex items-center justify-center gap-2"
            >
                <Sparkles className="w-6 h-6" />
                {isGenerating ? 'Wird geschrieben...' : 'Geschichte jetzt schreiben'}
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

import { useStore } from '../store/useStore';
import { deleteStory, revoiceStory, getVoicePreviewUrl, exportStoryToKindle } from '../lib/api';
import { Play, Trash2, BookOpen, Calendar, Loader2, Mic, X, Check, Venus, Mars, Users, Pause, Sparkles, Send } from 'lucide-react';
import toast from 'react-hot-toast';
import { useEffect, useState, useRef } from 'react';

const AUTHOR_LAST_NAMES: Record<string, string> = {
    kehlmann: 'Kehlmann',
    zeh: 'Zeh',
    fitzek: 'Fitzek',
    sueskind: 'Süskind',
    kracht: 'Kracht',
    bachmann: 'Bachmann',
    kafka: 'Kafka',
    borchert: 'Borchert',
    jaud: 'Jaud',
    regener: 'Regener',
    strunk: 'Strunk',
    kling: 'Kling',
    stuckrad_barre: 'Stuckrad-Barre',
    evers: 'Evers',
    funke: 'Funke',
    pantermueller: 'Pantermüller',
    auer: 'Auer'
};

export default function StoryArchive() {
    const { stories, voices, setActiveView, setSelectedStoryId, loadStories, updateStorySpotify } = useStore();
    const [revoiceTarget, setRevoiceTarget] = useState<string | null>(null);
    const [selectedVoice, setSelectedVoice] = useState<string>('seraphina');
    const [isRevoicing, setIsRevoicing] = useState(false);
    const [confirmRevoice, setConfirmRevoice] = useState(false);
    const [previewVoice, setPreviewVoice] = useState<string | null>(null);
    const [kindleEmail, setKindleEmail] = useState<string>(() => localStorage.getItem('kindle_email') || 'dirk.proessel.runthaler@kindle.com');
    const [isExporting, setIsExporting] = useState<string | null>(null);
    const [showKindleModal, setShowKindleModal] = useState<string | null>(null);
    const audioRef = useRef<HTMLAudioElement>(null);

    useEffect(() => {
        window.scrollTo(0, 0);
    }, []);

    const formatDuration = (seconds: number | null) => {
        if (!seconds) return '—';
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m}:${s.toString().padStart(2, '0')}`;
    };

    const formatDate = (dateStr: string) => {
        const d = new Date(dateStr);
        return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    };

    const handlePlay = (id: string) => {
        setSelectedStoryId(id);
        setActiveView('player');
    };

    const handleDelete = async (id: string, title: string) => {
        if (!confirm(`"${title}" wirklich löschen?`)) return;
        try {
            await deleteStory(id);
            await loadStories();
            toast.success('Geschichte gelöscht');
        } catch {
            toast.error('Fehler beim Löschen');
        }
    };

    const handleSpotifyToggle = async (id: string, enabled: boolean) => {
        try {
            await updateStorySpotify(id, enabled);
            toast.success(enabled ? 'Zu Spotify hinzugefügt' : 'Von Spotify entfernt');
        } catch {
            toast.error('Fehler beim Aktualisieren');
        }
    };

    const handleRevoice = async () => {
        if (!revoiceTarget) return;
        setIsRevoicing(true);
        try {
            await revoiceStory(revoiceTarget, selectedVoice);
            toast.success('Neuvertonung gestartet');
            setRevoiceTarget(null);
            setConfirmRevoice(false);
            await loadStories();
        } catch (error) {
            toast.error('Fehler beim Starten der Neuvertonung');
        } finally {
            setIsRevoicing(false);
        }
    };

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

    const handleKindleExport = async (id: string) => {
        if (!kindleEmail) {
            toast.error('Bitte Kindle E-Mail Adresse eingeben');
            return;
        }
        localStorage.setItem('kindle_email', kindleEmail);
        setIsExporting(id);
        try {
            await exportStoryToKindle(id, kindleEmail);
            toast.success('An Kindle gesendet!');
            setShowKindleModal(null);
        } catch (error: any) {
            toast.error(error.message || 'Fehler beim Kindle-Export');
        } finally {
            setIsExporting(null);
        }
    };

    return (
        <div className="p-4 sm:p-6 max-w-2xl mx-auto">
            <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 mb-4 shadow-lg shadow-amber-400/25">
                    <BookOpen className="w-8 h-8 text-white" />
                </div>
                <h1 className="text-2xl font-bold text-slate-900">Archiv</h1>
                <p className="text-slate-500 mt-1">{stories.length} Geschichte{stories.length !== 1 ? 'n' : ''}</p>
            </div>

            {stories.length === 0 ? (
                <div className="text-center py-16">
                    <div className="w-16 h-16 mx-auto bg-slate-100 rounded-2xl flex items-center justify-center mb-4">
                        <BookOpen className="w-8 h-8 text-slate-300" />
                    </div>
                    <p className="text-slate-400 text-sm">Noch keine Geschichten erstellt</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {stories.map(story => (
                        <div
                            key={story.id}
                            className="bg-white border-2 border-slate-100 rounded-2xl p-4 hover:border-slate-200 transition-all group"
                        >
                            <div className="flex items-start gap-4">
                                {story.image_url ? (
                                    <div
                                        className="w-20 h-20 rounded-xl overflow-hidden shrink-0 shadow-sm border border-slate-100 cursor-pointer"
                                        onClick={() => handlePlay(story.id)}
                                    >
                                        <img src={story.image_url} alt={story.title} className="w-full h-full object-cover" />
                                    </div>
                                ) : (
                                    <div
                                        className="w-20 h-20 rounded-xl bg-slate-50 flex items-center justify-center shrink-0 border border-slate-100 cursor-pointer"
                                        onClick={() => handlePlay(story.id)}
                                    >
                                        <BookOpen className="w-8 h-8 text-slate-200" />
                                    </div>
                                )}
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="flex-1 min-w-0 cursor-pointer" onClick={() => story.status === 'done' && handlePlay(story.id)}>
                                            <h3 className="font-bold text-slate-900 truncate group-hover:text-indigo-600 transition-colors">
                                                {story.title}
                                            </h3>

                                            {story.status === 'generating' ? (
                                                <div className="mt-3 space-y-2 w-full">
                                                    <div className="flex justify-between items-end">
                                                        <div className="flex items-center gap-2 text-indigo-600 text-xs font-semibold animate-pulse">
                                                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                            {story.progress || 'Wird erstellt...'}
                                                        </div>
                                                        <span className="text-[10px] font-bold text-indigo-400 bg-indigo-50 px-1.5 py-0.5 rounded-md">
                                                            {story.progress_pct || 0}%
                                                        </span>
                                                    </div>
                                                    <div className="w-full h-1.5 bg-indigo-50 rounded-full overflow-hidden border border-indigo-100/50">
                                                        <div
                                                            className="h-full bg-gradient-to-r from-indigo-400 to-purple-500 transition-all duration-500 ease-out"
                                                            style={{ width: `${story.progress_pct || 0}%` }}
                                                        />
                                                    </div>
                                                </div>
                                            ) : story.status === 'error' ? (
                                                <div className="mt-2 px-3 py-1.5 bg-red-50 text-red-600 rounded-lg text-xs font-medium w-fit border border-red-100 italic">
                                                    {story.progress || 'Fehler bei der Erstellung'}
                                                </div>
                                            ) : (
                                                <div className="mt-1 space-y-2">
                                                    {/* The Idea / Prompt */}
                                                    <div className="bg-slate-50 border border-slate-100 rounded-lg p-2 text-[11px] text-slate-500 italic">
                                                        <span className="font-bold uppercase tracking-wider text-[9px] block mb-0.5 text-slate-400 not-italic">Idee:</span>
                                                        {story.prompt}
                                                    </div>

                                                    {/* Full Synopsis */}
                                                    <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-wrap">{story.description}</p>

                                                    {/* Detailed Metadata Grid */}
                                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 border-t border-slate-50">
                                                        <div className="flex flex-col">
                                                            <span className="text-[9px] uppercase font-bold text-slate-400">Genre</span>
                                                            <span className="text-[11px] text-slate-600 truncate font-semibold">{story.genre || '—'}</span>
                                                        </div>
                                                        <div className="flex flex-col">
                                                            <span className="text-[9px] uppercase font-bold text-slate-400">Stil</span>
                                                            <span className="text-[11px] text-slate-600 truncate font-semibold">
                                                                {story.style.split(',').map(s => AUTHOR_LAST_NAMES[s.trim()] || s).join(', ')}
                                                            </span>
                                                        </div>
                                                        <div className="flex flex-col">
                                                            <span className="text-[9px] uppercase font-bold text-slate-400">Stimme</span>
                                                            <span className="text-[11px] text-slate-600 truncate font-semibold capitalize">
                                                                {story.voice_name || story.voice_key}
                                                            </span>
                                                        </div>
                                                        <div className="flex flex-col">
                                                            <span className="text-[9px] uppercase font-bold text-slate-400">Dauer</span>
                                                            <span className="text-[11px] text-slate-600 truncate font-semibold">{formatDuration(story.duration_seconds)}</span>
                                                        </div>
                                                    </div>

                                                    {/* Date & Info Row */}
                                                    <div className="flex items-center gap-3 text-[10px] text-slate-400 pt-1">
                                                        <span className="flex items-center gap-1">
                                                            <BookOpen className="w-3 h-3" />
                                                            {story.word_count ? `${story.word_count} Worte` : `${story.chapter_count} Kapitel`}
                                                        </span>
                                                        <span className="flex items-center gap-1">
                                                            <Calendar className="w-3 h-3" />
                                                            {formatDate(story.created_at)}
                                                        </span>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100">
                                        <div className="flex items-center gap-4">
                                            <button
                                                onClick={() => handlePlay(story.id)}
                                                disabled={story.status !== 'done'}
                                                className="flex items-center gap-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-700 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                            >
                                                <Play className="w-3.5 h-3.5" />
                                                Anhören
                                            </button>
                                            <button
                                                onClick={() => {
                                                    setRevoiceTarget(story.id);
                                                    setSelectedVoice(story.voice_key || 'seraphina');
                                                }}
                                                disabled={story.status !== 'done'}
                                                className="flex items-center gap-1.5 text-xs font-medium text-amber-600 hover:text-amber-700 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                            >
                                                <Mic className="w-3.5 h-3.5" />
                                                Neu vertonen
                                            </button>
                                            <button
                                                onClick={() => setShowKindleModal(story.id)}
                                                disabled={story.status !== 'done' || isExporting === story.id}
                                                className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 hover:text-emerald-700 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                            >
                                                {isExporting === story.id ? (
                                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                ) : (
                                                    <Send className="w-3.5 h-3.5" />
                                                )}
                                                Kindle Export
                                            </button>
                                            <label className={`flex items-center gap-1.5 cursor-pointer group/toggle ${story.status !== 'done' ? 'opacity-30 cursor-not-allowed' : ''}`}>
                                                <div className="relative">
                                                    <input
                                                        type="checkbox"
                                                        className="sr-only"
                                                        disabled={story.status !== 'done'}
                                                        checked={story.is_on_spotify}
                                                        onChange={(e) => handleSpotifyToggle(story.id, e.target.checked)}
                                                    />
                                                    <div className={`w-9 h-5 rounded-full transition-colors ${story.is_on_spotify ? 'bg-green-500' : 'bg-slate-200'}`}></div>
                                                    <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${story.is_on_spotify ? 'translate-x-4' : ''}`}></div>
                                                </div>
                                                <span className={`text-xs font-medium transition-colors ${story.is_on_spotify ? 'text-green-600' : 'text-slate-400'}`}>
                                                    Spotify Feed
                                                </span>
                                            </label>
                                        </div>
                                        <button
                                            onClick={() => handleDelete(story.id, story.title)}
                                            className="p-1 text-slate-300 hover:text-red-400 transition-colors"
                                            title="Löschen"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Re-voice Modal */}
            {revoiceTarget && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
                    <div className="bg-white rounded-3xl w-full max-w-md shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
                        <div className="p-6">
                            <div className="flex items-center justify-between mb-6">
                                <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                                    <Mic className="w-5 h-5 text-indigo-600" />
                                    Neu vertonen
                                </h2>
                                <button
                                    onClick={() => { setRevoiceTarget(null); setConfirmRevoice(false); }}
                                    className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            {!confirmRevoice ? (
                                <>
                                    <p className="text-sm text-slate-500 mb-4">Wähle eine neue Stimme für diese Geschichte:</p>
                                    <div className="grid grid-cols-1 gap-2 max-h-[300px] overflow-y-auto mb-6 pr-1 custom-scrollbar">
                                        {voices.map(v => (
                                            <div
                                                key={v.key}
                                                className={`p-3 rounded-xl transition-all border-2 cursor-pointer flex items-center justify-between ${selectedVoice === v.key
                                                    ? 'border-indigo-500 bg-indigo-50 shadow-sm'
                                                    : 'border-slate-100 bg-white hover:border-slate-200'
                                                    }`}
                                                onClick={() => setSelectedVoice(v.key)}
                                            >
                                                <div className="flex items-center gap-3">
                                                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${selectedVoice === v.key ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-50 text-slate-400'}`}>
                                                        {v.gender === 'female' ? <Venus className="w-4 h-4" /> :
                                                            v.gender === 'male' ? <Mars className="w-4 h-4" /> : <Users className="w-4 h-4" />}
                                                    </div>
                                                    <div>
                                                        <div className={`text-xs font-bold capitalize ${selectedVoice === v.key ? 'text-indigo-700' : 'text-slate-700'}`}>
                                                            {v.name}
                                                        </div>
                                                        <div className={`text-[10px] ${selectedVoice === v.key ? 'text-indigo-500' : 'text-slate-400'}`}>
                                                            {v.engine === 'gemini' ? 'Premium ($)' : 'Standard'}
                                                        </div>
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); handlePreviewVoice(v.key); }}
                                                    className={`w-7 h-7 rounded-full flex items-center justify-center transition-all shrink-0 ${previewVoice === v.key
                                                        ? 'bg-indigo-500 text-white'
                                                        : 'bg-slate-100 text-slate-400 hover:bg-slate-200'
                                                        }`}
                                                >
                                                    {previewVoice === v.key ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3 ml-0.5" />}
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                    <button
                                        onClick={() => setConfirmRevoice(true)}
                                        className="w-full bg-indigo-600 text-white py-3 rounded-xl font-bold text-sm shadow-lg shadow-indigo-100 hover:bg-indigo-700 transition-colors"
                                    >
                                        Weiter
                                    </button>
                                </>
                            ) : (
                                <div className="text-center py-4">
                                    <div className="w-16 h-16 bg-amber-50 rounded-full flex items-center justify-center mx-auto mb-4">
                                        <Sparkles className="w-8 h-8 text-amber-500" />
                                    </div>
                                    <h3 className="font-bold text-slate-900 text-lg mb-2">Bist du sicher?</h3>
                                    <p className="text-sm text-slate-500 mb-8 leading-relaxed">
                                        Die aktuelle Audio-Version dieser Geschichte wird durch eine neue Vertonung mit der Stimme <span className="font-bold text-indigo-600 capitalize">{voices.find(v => v.key === selectedVoice)?.name}</span> ersetzt. Dieser Vorgang dauert ein paar Minuten.
                                    </p>
                                    <div className="flex gap-3">
                                        <button
                                            onClick={() => setConfirmRevoice(false)}
                                            className="flex-1 px-4 py-3 rounded-xl font-bold text-sm text-slate-400 hover:bg-slate-50 transition-colors"
                                        >
                                            Zurück
                                        </button>
                                        <button
                                            onClick={handleRevoice}
                                            disabled={isRevoicing}
                                            className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-3 rounded-xl font-bold text-sm shadow-lg shadow-indigo-100 hover:opacity-90 transition-all flex items-center justify-center gap-2"
                                        >
                                            {isRevoicing ? (
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                            ) : (
                                                <Check className="w-4 h-4" />
                                            )}
                                            Ja, neu vertonen
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Kindle Export Modal */}
            {showKindleModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
                    <div className="bg-white rounded-3xl w-full max-w-sm shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
                        <div className="p-6">
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                                    <Send className="w-5 h-5 text-emerald-600" />
                                    Kindle Export
                                </h2>
                                <button
                                    onClick={() => setShowKindleModal(null)}
                                    className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            <p className="text-sm text-slate-500 mb-6">
                                Gib deine Kindle E-Mail Adresse ein, um die Geschichte als E-Book zu senden.
                            </p>

                            <div className="space-y-4">
                                <div>
                                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5 ml-1">
                                        Kindle E-Mail Adresse
                                    </label>
                                    <input
                                        type="email"
                                        value={kindleEmail}
                                        onChange={(e) => setKindleEmail(e.target.value)}
                                        placeholder="beispiel@kindle.com"
                                        className="w-full px-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl focus:border-emerald-500 focus:ring-0 transition-all text-sm font-medium"
                                    />
                                </div>

                                <button
                                    onClick={() => handleKindleExport(showKindleModal)}
                                    disabled={isExporting === showKindleModal}
                                    className="w-full bg-emerald-600 text-white py-3 rounded-xl font-bold text-sm shadow-lg shadow-emerald-100 hover:bg-emerald-700 transition-colors flex items-center justify-center gap-2"
                                >
                                    {isExporting === showKindleModal ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <Send className="w-4 h-4" />
                                    )}
                                    Jetzt senden
                                </button>

                                <p className="text-[10px] text-slate-400 text-center leading-relaxed">
                                    Stelle sicher, dass <span className="text-slate-600 font-semibold">dirk.proessel@gmail.com</span> in deinem Amazon-Konto als zugelassener Absender eingetragen ist.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}
            <audio ref={audioRef} className="hidden" />
        </div>
    );
}

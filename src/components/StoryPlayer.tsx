import { useState, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { getAudioUrl, fetchStory, getRssFeedUrl, getThumbUrl, type StoryDetail } from '../lib/api';
import {
    Play, Pause, SkipBack, SkipForward,
    ChevronDown, ChevronUp, Rss, Copy, ArrowLeft, Moon, BookOpen, Send, Loader2, X, Calendar, Mic, Sparkles, MessageCircle
} from 'lucide-react';
import { AUTHOR_NAMES } from '../lib/authors';
import { voiceName } from '../lib/voices';
import toast from 'react-hot-toast';
import { exportStoryToKindle } from '../lib/api';

export default function StoryPlayer() {
    const { selectedStoryId, setActiveView } = useStore();
    const [story, setStory] = useState<StoryDetail | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [isDragging, setIsDragging] = useState(false);
    const [dragTime, setDragTime] = useState(0);
    const [showChapters, setShowChapters] = useState(false);
    const [showRss, setShowRss] = useState(false);
    // Store actions to trigger re-voice modal
    const { user, updateStorySpotify, setRevoiceStoryId } = useStore();
    const [isExporting, setIsExporting] = useState(false);
    const [showKindleModal, setShowKindleModal] = useState(false);
    const [kindleEmail, setKindleEmail] = useState<string>(() => user?.kindle_email || localStorage.getItem('kindle_email') || '');

    // Use DOM element instead of memory object for iOS Safari compatibility
    const audioRef = useRef<HTMLAudioElement>(null);

    // Attach event listeners once on mount
    useEffect(() => {
        const audio = audioRef.current;
        if (!audio) return;

        const onTimeUpdate = () => setCurrentTime(audio.currentTime);
        const onLoaded = () => { if (audio.duration && isFinite(audio.duration) && audio.duration > 0) setDuration(audio.duration); };
        const onEnded = () => setIsPlaying(false);
        const onPlay = () => setIsPlaying(true);
        const onPause = () => setIsPlaying(false);

        audio.addEventListener('timeupdate', onTimeUpdate);
        audio.addEventListener('loadedmetadata', onLoaded);
        audio.addEventListener('durationchange', onLoaded);
        audio.addEventListener('canplay', onLoaded);
        audio.addEventListener('ended', onEnded);
        audio.addEventListener('play', onPlay);
        audio.addEventListener('pause', onPause);

        return () => {
            audio.pause();
            audio.removeEventListener('timeupdate', onTimeUpdate);
            audio.removeEventListener('loadedmetadata', onLoaded);
            audio.removeEventListener('durationchange', onLoaded);
            audio.removeEventListener('canplay', onLoaded);
            audio.removeEventListener('ended', onEnded);
            audio.removeEventListener('play', onPlay);
            audio.removeEventListener('pause', onPause);
        };
    }, []);

    // Load new audio when story changes
    useEffect(() => {
        const audio = audioRef.current;
        if (!audio) return;
        setCurrentTime(0);
        setDuration(0);
        setIsPlaying(false);
        if (selectedStoryId && story?.voice_key !== 'none') {
            audio.src = getAudioUrl(selectedStoryId);
            audio.load();
        } else {
            audio.src = '';
        }
    }, [selectedStoryId, story?.voice_key]);

    // Fetch story metadata
    useEffect(() => {
        setStory(null);
        if (selectedStoryId) {
            fetchStory(selectedStoryId)
                .then(s => {
                    setStory(s);
                    // Use API duration as fallback (iOS Safari often can't read MP3 duration)
                    if (s.duration_seconds && s.duration_seconds > 0) {
                        setDuration(prev => prev > 0 ? prev : s.duration_seconds!);
                    }
                })
                .catch(() => toast.error('Geschichte konnte nicht geladen werden'));
        }
    }, [selectedStoryId]);

    const togglePlay = () => {
        const audio = audioRef.current;
        if (!audio) return;
        if (isPlaying) {
            audio.pause();
        } else {
            // Ensure audio source is loaded (defensive for iOS)
            if (!audio.src && selectedStoryId) {
                audio.src = getAudioUrl(selectedStoryId);
                audio.load();
            }
            const playPromise = audio.play();
            if (playPromise !== undefined) {
                playPromise.catch(err => {
                    console.warn("Playback failed:", err.name, err.message);
                    // AbortError = audio not ready yet → auto-retry when ready
                    if (err.name === 'AbortError' || err.name === 'NotSupportedError') {
                        const onReady = () => {
                            audio.removeEventListener('canplay', onReady);
                            audio.play().catch(() => {});
                        };
                        audio.addEventListener('canplay', onReady, { once: true });
                        audio.load();
                    }
                    // NotAllowedError = genuine iOS autoplay block (should be rare from tap)
                    // Don't show toast — just let the user tap again naturally
                });
            }
        }
    };

    const skip = (seconds: number) => {
        const audio = audioRef.current;
        if (!audio) return;
        audio.currentTime = Math.max(0, Math.min(audio.currentTime + seconds, duration));
    };

    // Proper seek: while dragging only move the slider visually.
    // Only actually seek the audio when pointer is released.
    const handleSeekChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setDragTime(parseFloat(e.target.value));
    };

    const handleSeekStart = (e: React.PointerEvent<HTMLInputElement>) => {
        setIsDragging(true);
        setDragTime(parseFloat((e.target as HTMLInputElement).value));
    };

    const handleSeekEnd = (e: React.PointerEvent<HTMLInputElement>) => {
        const time = parseFloat((e.target as HTMLInputElement).value);
        if (audioRef.current) {
            audioRef.current.currentTime = time;
        }
        setCurrentTime(time);
        setIsDragging(false);
    };

    const sliderValue = isDragging ? dragTime : currentTime;

    const formatTime = (s: number) => {
        if (!s || !isFinite(s)) return '0:00';
        const m = Math.floor(s / 60);
        const sec = Math.floor(s % 60);
        return `${m}:${sec.toString().padStart(2, '0')}`;
    };

    const copyRssUrl = () => {
        navigator.clipboard.writeText(getRssFeedUrl());
        toast.success('RSS-Feed URL kopiert!');
    };

    const handleKindleExport = async () => {
        if (!selectedStoryId) return;
        if (!user) {
            setActiveView('login');
            toast.error('Bitte melde dich an, um Kindle-Export zu nutzen');
            return;
        }
        if (!kindleEmail) {
            toast.error('Bitte Kindle E-Mail Adresse eingeben');
            return;
        }
        setIsExporting(true);
        try {
            await exportStoryToKindle(selectedStoryId, kindleEmail);
            toast.success('An Kindle gesendet!');
            setShowKindleModal(false);
        } catch (error: any) {
            toast.error(error.message || 'Fehler beim Kindle-Export');
        } finally {
            setIsExporting(false);
        }
    };

    const handleSpotifyToggle = async (enabled: boolean) => {
        if (!selectedStoryId) return;
        try {
            await updateStorySpotify(selectedStoryId, enabled);
            toast.success(enabled ? 'Zu Spotify hinzugefügt' : 'Von Spotify entfernt');
            // Refresh local story state
            if (story) setStory({ ...story, is_on_spotify: enabled });
        } catch {
            toast.error('Fehler beim Aktualisieren');
        }
    };


    return (
        <>
            {/* Audio Element for iOS Compatibility */}
            <audio ref={audioRef} preload="auto" playsInline />

            {!selectedStoryId ? (
                <div className="p-6 flex flex-col items-center justify-center min-h-[60vh]">
                    <Moon className="w-12 h-12 text-slate-200 mb-4" />
                    <p className="text-slate-400 text-sm">Wähle eine Geschichte aus dem Archiv</p>
                </div>
            ) : !story ? (
                <div className="p-6 flex flex-col items-center justify-center min-h-[60vh]">
                    <div className="w-16 h-16 rounded-full border-4 border-[#F0FDF4] border-t-[#2D5A4C] animate-spin mb-4" />
                    <p className="text-slate-400 text-sm">Lade Geschichte…</p>
                </div>
            ) : (
                <div className="p-4 sm:p-6 max-w-2xl mx-auto">
                    {/* Back button */}
                    <button
                        onClick={() => setActiveView('archive')}
                        className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-600 transition-colors mb-6"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Zurück zum Archiv
                    </button>

                    {/* Cover / Title */}
                    <div className="text-center mb-8">
                        {story.image_url ? (
                            <div className="w-48 h-48 mx-auto rounded-3xl overflow-hidden mb-6 shadow-xl border-4 border-white">
                                <img src={getThumbUrl(story.id)} alt={story.title} className="w-full h-full object-cover" />
                            </div>
                        ) : (
                            <div className="w-32 h-32 mx-auto rounded-3xl bg-[#D1FAE5] flex items-center justify-center mb-6 shadow-xl shadow-[#2D5A4C]/10">
                                <Moon className="w-16 h-16 text-white/90" />
                            </div>
                        )}
                        <h1 className="text-2xl font-bold text-slate-900 font-serif">{story.title}</h1>

                        {/* Metadata Row */}
                        <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 mt-3 text-[11px] font-medium text-slate-500">
                            {story.genre && (
                                <div className="flex items-center gap-1">
                                    <span className="text-slate-400">Genre:</span>
                                    <span className="text-slate-700">{story.genre}</span>
                                </div>
                            )}
                            {story.style && (
                                <div className="flex items-center gap-1">
                                    <span className="text-slate-400">Stil:</span>
                                    <span
                                        className="text-slate-700 cursor-help border-b border-dotted border-slate-300"
                                        title={story.style.split(',').map(s => AUTHOR_NAMES[s.trim().toLowerCase()] || s.trim().toLowerCase()).join(', ')}
                                    >
                                        {story.style.split(',').map(s => AUTHOR_NAMES[s.trim().toLowerCase()] || s.trim().toLowerCase()).join(', ')}
                                    </span>
                                </div>
                            )}
                            <div className="flex items-center gap-1">
                                <span className="text-slate-400">Stimme:</span>
                                <span className="text-slate-700">
                                    {voiceName(story.voice_key)}
                                </span>
                            </div>
                        </div>

                        <p className="text-xs text-slate-400 mt-3 flex items-center justify-center gap-2">
                            <span className="flex items-center gap-1">
                                <BookOpen className="w-3.5 h-3.5" />
                                {story.word_count ? `${story.word_count} Worte` : `${story.chapter_count} Kapitel`}
                            </span>
                            <span>·</span>
                            <span>{formatTime(story.duration_seconds || 0)}</span>
                        </p>
                    </div>

                    {/* Action Buttons (Kindle / Spotify / WhatsApp) */}
                    <div className="flex items-center justify-center gap-3 mb-8">
                        {user && (
                            <button
                                onClick={() => setShowKindleModal(true)}
                                className="flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-600 rounded-xl text-xs font-bold hover:bg-emerald-100 transition-all border border-emerald-100"
                            >
                                <Send className="w-3.5 h-3.5" />
                                Kindle
                            </button>
                        )}
                        {user && (
                            <button
                                onClick={() => handleSpotifyToggle(!story.is_on_spotify)}
                                disabled={user.is_admin && story.user_id !== user.id}
                                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all border ${
                                    story.is_on_spotify 
                                    ? 'bg-green-50 text-green-600 border-green-100' 
                                    : 'bg-slate-50 text-slate-500 border-slate-100 opacity-60 hover:opacity-100'
                                } ${(user.is_admin && story.user_id !== user.id) ? 'opacity-30 cursor-not-allowed hidden' : ''}`}
                            >
                                <Calendar className="w-3.5 h-3.5" />
                                Spotify
                            </button>
                        )}
                        <button
                            onClick={() => {
                                const shareUrl = `${window.location.origin}${window.location.pathname}#/player/${story.id}`;
                                const text = `Schau mal, ich habe eine neue Geschichte erstellt: *${story.title}* 🌙✨\n\n${story.description}\n\nHör sie dir hier an:\n${shareUrl}`;
                                window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
                            }}
                            className="flex items-center gap-2 px-4 py-2 bg-green-50 text-green-600 rounded-xl text-xs font-bold hover:bg-green-100 transition-all border border-green-100"
                        >
                            <MessageCircle className="w-3.5 h-3.5" />
                            WhatsApp
                        </button>
                    </div>


                    {/* Progress / Audio Controls */}
                    {story.voice_key !== 'none' ? (
                        <>
                            {/* Progress */}
                            <div className="mb-4">
                                <input
                                    type="range"
                                    min={0}
                                    max={duration || 0}
                                    step={1}
                                    value={sliderValue}
                                    onChange={handleSeekChange}
                                    onPointerDown={handleSeekStart}
                                    onPointerUp={handleSeekEnd}
                                    className="w-full h-1.5 rounded-full bg-slate-200 accent-[#2D5A4C] cursor-pointer appearance-none [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[#2D5A4C] [&::-webkit-slider-thumb]:shadow-md"
                                />
                                <div className="flex justify-between text-xs text-slate-400 mt-1">
                                    <span>{formatTime(sliderValue)}</span>
                                    <span>{formatTime(duration)}</span>
                                </div>
                            </div>

                            {/* Controls */}
                            <div className="flex items-center justify-center gap-6 mb-8">
                                <button onClick={() => skip(-30)} className="w-12 h-12 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 flex items-center justify-center transition-all">
                                    <SkipBack className="w-5 h-5" />
                                </button>
                                <button
                                    onClick={togglePlay}
                                    className="w-16 h-16 rounded-2xl bg-[#2D5A4C] text-white flex items-center justify-center shadow-lg shadow-[#2D5A4C]/25 hover:shadow-[#2D5A4C]/40 transition-all active:scale-95"
                                >
                                    {isPlaying ? <Pause className="w-7 h-7" /> : <Play className="w-7 h-7 ml-1" />}
                                </button>
                                <button onClick={() => skip(30)} className="w-12 h-12 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 flex items-center justify-center transition-all">
                                    <SkipForward className="w-5 h-5" />
                                </button>
                            </div>
                        </>
                    ) : (
                        <div className="mb-8 p-6 bg-[#F0FDF4] rounded-2xl border-2 border-[#D1FAE5] border-dashed text-center">
                            <Mic className="w-8 h-8 text-[#2D5A4C]/60 mx-auto mb-3" />
                            <p className="text-sm font-medium text-slate-600 mb-4">Diese Geschichte hat noch keine Vertonung.</p>
                            <button
                                onClick={() => {
                                    setRevoiceStoryId(story.id);
                                    setActiveView('archive');
                                }}
                                className="inline-flex items-center gap-2 px-6 py-2.5 bg-[#2D5A4C] text-white rounded-xl text-sm font-bold shadow-md hover:bg-[#1A4336] transition-all active:scale-95"
                            >
                                <Sparkles className="w-4 h-4" />
                                Jetzt vertonen
                            </button>
                        </div>
                    )}

                    {/* Chapters Toggle */}
                    {story.chapters && story.chapters.length > 0 && (
                        <div className="mb-4">
                            <button
                                onClick={() => setShowChapters(!showChapters)}
                                className="w-full flex items-center justify-between p-4 bg-white border-2 border-slate-100 rounded-2xl hover:border-slate-200 transition-all"
                            >
                                <span className="text-sm font-semibold text-slate-700 font-serif">📖 Kurzgeschichten-Text</span>
                                {showChapters ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                            </button>
                            {showChapters && (
                                <div className="mt-2 p-6 bg-white border-2 border-slate-100 rounded-2xl">
                                    <p className="text-base text-slate-700 leading-relaxed whitespace-pre-line font-serif">
                                        {story.chapters.map(ch => ch.text).join('\n\n')}
                                    </p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* RSS Feed (Admin/Owner only or just hidden for Guest/Std?) - Plan says "Kein Podcast RSS-Feed im Player sichtbar" for Standard & Guest */}
                    {user?.is_admin && (
                        <div className="mb-4">
                            <button
                                onClick={() => setShowRss(!showRss)}
                                className="w-full flex items-center justify-between p-4 bg-white border-2 border-slate-100 rounded-2xl hover:border-slate-200 transition-all"
                            >
                                <span className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                                    <Rss className="w-4 h-4 text-orange-500" />
                                    Podcast-Feed
                                </span>
                                {showRss ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                            </button>
                            {showRss && (
                                <div className="mt-2 p-4 bg-white border-2 border-slate-100 rounded-2xl">
                                    <p className="text-xs text-slate-500 mb-3">Füge diese URL in deine Podcast-App ein:</p>
                                    <div className="flex items-center gap-2">
                                        <code className="flex-1 text-xs bg-slate-50 text-slate-600 p-2.5 rounded-lg truncate">
                                            {getRssFeedUrl()}
                                        </code>
                                        <button
                                            onClick={copyRssUrl}
                                            className="shrink-0 w-10 h-10 rounded-xl bg-slate-50 text-slate-400 flex items-center justify-center hover:bg-[#F0FDF4] hover:text-[#2D5A4C] transition-colors"
                                        >
                                            <Copy className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
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
                                    onClick={() => setShowKindleModal(false)}
                                    className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            <p className="text-sm text-slate-500 mb-6">
                                Sende diese Geschichte als E-Book auf deinen Kindle.
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
                                    onClick={handleKindleExport}
                                    disabled={isExporting}
                                    className="w-full bg-emerald-600 text-white py-3 rounded-xl font-bold text-sm shadow-lg shadow-emerald-100 hover:bg-emerald-700 transition-colors flex items-center justify-center gap-2"
                                >
                                    {isExporting ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <Send className="w-4 h-4" />
                                    )}
                                    Jetzt senden
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}

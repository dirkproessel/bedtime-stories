import { useStore } from '../store/useStore';
import { deleteStory, revoiceStory, getVoicePreviewUrl, exportStoryToKindle, getThumbUrl, regenerateStoryImage } from '../lib/api';
import { Play, Trash2, BookOpen, Calendar, Loader2, Mic, X, Venus, Mars, Users, Pause, Send, ChevronLeft, ChevronRight, Image as ImageIcon, RefreshCw, Sparkles, Settings2, MessageCircle, Feather } from 'lucide-react';
import toast from 'react-hot-toast';
import { useEffect, useState, useRef } from 'react';


import { voiceName, voiceDesc } from '../lib/voices';

export default function StoryArchive() {
    const { 
        stories, loadStories, setActiveView, 
        toggleStoryVisibility, user, archiveFilter, setArchiveFilter,
        totalStories, totalMyStories, totalPublicStories,
        currArchivePage, voices, revoiceStoryId, setRevoiceStoryId,
        updateStorySpotify, startGeneration,
        setGeneratorPrompt, setGeneratorGenre, setGeneratorAuthors,
        setGeneratorMinutes, setGeneratorVoice, setGeneratorRemix,
        setReaderOpen
    } = useStore();
    const [selectedVoice, setSelectedVoice] = useState('seraphina');
    const [confirmRevoice, setConfirmRevoice] = useState(false);
    const [revoicingId, setRevoicingId] = useState<string | null>(null);
    const [previewVoice, setPreviewVoice] = useState<string | null>(null);
    const [kindleEmail, setKindleEmail] = useState<string>(() => user?.kindle_email || localStorage.getItem('kindle_email') || 'dirk.proessel.runthaler@kindle.com');
    const [isExporting, setIsExporting] = useState<string | null>(null);
    const [showKindleModal, setShowKindleModal] = useState<string | null>(null);
    const [isPublicLoading, setIsPublicLoading] = useState<string | null>(null);
    const [showRemixModal, setShowRemixModal] = useState<string | null>(null);
    const [remixType, setRemixType] = useState<'improvement' | 'sequel'>('improvement');
    const [remixInstructions, setRemixInstructions] = useState('');
    const [isRemixing, setIsRemixing] = useState(false);
    const audioRef = useRef<HTMLAudioElement>(null);

    // Track if we have performed the initial check for "my" stories
    const [initialCheckDone, setInitialCheckDone] = useState(false);

    useEffect(() => {
        // First load with the initial filter
        loadStories(1);
    }, []);

    // Effect to switch to "public" if "my" is empty on first load
    useEffect(() => {
        if (!initialCheckDone && totalStories !== undefined) {
            if (archiveFilter === 'my' && totalMyStories === 0 && totalPublicStories > 0) {
                setArchiveFilter('public');
                loadStories(1);
            }
            setInitialCheckDone(true);
        }
    }, [totalMyStories, totalPublicStories, totalStories, initialCheckDone, archiveFilter, loadStories, setArchiveFilter]);


    const handlePageChange = (page: number) => {
        loadStories(page);
        document.getElementById('main-scroll-container')?.scrollTo({ top: 0, behavior: 'smooth' });
    };


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
        setReaderOpen(true, id);
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

    const handleRegenerateImage = async (id: string) => {
        try {
            await regenerateStoryImage(id);
            toast.success('Bild-Regenerierung gestartet!');
        } catch (error: any) {
            toast.error(error.message || 'Fehler beim Starten');
        }
    };

    const handleRemix = async (storyId: string) => {
        const story = stories.find(s => s.id === storyId);
        if (!story) return;

        setIsRemixing(true);
        try {
            await startGeneration({
                prompt: remixInstructions || (remixType === 'improvement' ? story.prompt : `Fortsetzung von ${story.title}`),
                genre: story.genre,
                style: story.style,
                target_minutes: story.duration_seconds ? Math.ceil(story.duration_seconds / 60) : 15,
                voice_key: story.voice_key,
                parent_id: storyId,
                remix_type: remixType,
                further_instructions: remixInstructions || undefined
            });
            toast.success(remixType === 'sequel' ? 'Fortsetzung wird generiert!' : 'Verbesserung wird generiert!');
            setShowRemixModal(null);
            setRemixInstructions('');
        } catch (error: any) {
            toast.error(error.message || 'Fehler beim Starten');
        } finally {
            setIsRemixing(false);
        }
    };

    const handleAdvancedRemix = (storyId: string) => {
        const story = stories.find(s => s.id === storyId);
        if (!story) return;

        // 1. Pre-fill basic settings
        setGeneratorGenre(story.genre);
        setGeneratorAuthors(story.style.split(',').map(s => s.trim()));
        setGeneratorMinutes(story.duration_seconds ? Math.ceil(story.duration_seconds / 60) : 15);
        setGeneratorVoice(story.voice_key);

        // 2. Pre-fill Idea based on type
        if (remixType === 'improvement') {
            setGeneratorPrompt(story.prompt);
            setGeneratorRemix(storyId, 'improvement', null);
        } else {
            setGeneratorPrompt(''); // Sequel always starts fresh
            setGeneratorRemix(storyId, 'sequel', { 
                title: story.title, 
                synopsis: story.description 
            });
        }

        // 3. Navigate
        setShowRemixModal(null);
        setActiveView('create');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    return (
        <div className="p-4 sm:p-6 max-w-2xl mx-auto">
            <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary mb-4 shadow-lg shadow-primary/20">
                    <Feather className="w-8 h-8 text-white" />
                </div>
                <h1 className="text-2xl font-bold text-text font-serif">
                    {archiveFilter === 'public' ? 'Entdecken' : 'Meine Bibliothek'}
                </h1>
            </div>

            {stories.length === 0 ? (
                <div className="text-center py-20 animate-in fade-in duration-700">
                    <div className="w-24 h-24 mx-auto bg-surface rounded-[2rem] flex items-center justify-center mb-6 shadow-sm border border-slate-800">
                        <Feather className="w-10 h-10 text-slate-700" />
                    </div>
                    <h2 className="font-serif text-2xl text-text mb-2 font-semibold">Dein Archiv ist noch leer</h2>
                    <p className="text-slate-500 text-sm max-w-[280px] mx-auto leading-relaxed">
                        Hier werden deine literarischen Werke sicher aufbewahrt. Erstelle deine erste Geschichte im Labor!
                    </p>
                    <button 
                        onClick={() => setActiveView('create')}
                        className="btn-primary mt-8 px-8"
                    >
                        Jetzt starten
                    </button>
                </div>
            ) : (
                <div className="space-y-3">
                    {stories.map(story => (
                        <div
                            key={story.id}
                            className="bg-surface border border-slate-800 rounded-[2.5rem] p-6 hover:shadow-xl hover:shadow-primary/5 transition-all duration-300 group mb-6"
                        >
                            <div className="flex items-start gap-4">
                                {story.image_url ? (
                                    <div
                                        className="w-24 h-24 rounded-[2rem] overflow-hidden shrink-0 shadow-sm border border-slate-700 cursor-pointer"
                                        onClick={() => handlePlay(story.id)}
                                    >
                                        <img src={getThumbUrl(story.id)} alt={story.title} className="w-full h-full object-cover grayscale-[20%]" />
                                    </div>
                                ) : (
                                    <div
                                        className="w-24 h-24 rounded-[2rem] bg-slate-900 flex items-center justify-center shrink-0 border border-slate-800 cursor-pointer"
                                        onClick={() => handlePlay(story.id)}
                                    >
                                        <Feather className="w-8 h-8 text-slate-700" />
                                    </div>
                                )}
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="flex-1 min-w-0 cursor-pointer" onClick={() => story.status === 'done' && handlePlay(story.id)}>
                                            <h3 className="font-serif text-xl font-semibold text-text group-hover:text-primary transition-colors leading-tight">
                                                {story.title}
                                            </h3>

                                            {story.status === 'generating' ? (
                                                <div className="mt-3 space-y-2 w-full">
                                                    <div className="flex justify-between items-end">
                                                        <div className="flex items-center gap-2 text-primary text-xs font-semibold animate-pulse">
                                                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                            {story.progress || 'Wird erstellt...'}
                                                        </div>
                                                        <span className="text-[10px] font-bold text-primary bg-accent/20 px-1.5 py-0.5 rounded-md">
                                                            {story.progress_pct || 0}%
                                                        </span>
                                                    </div>
                                                    <div className="w-full h-1.5 bg-accent/20 rounded-full overflow-hidden border border-primary/20">
                                                        <div
                                                            className="h-full bg-primary transition-all duration-500 ease-out"
                                                            style={{ width: `${story.progress_pct || 0}%` }}
                                                        />
                                                    </div>
                                                </div>
                                            ) : story.status === 'error' ? (
                                                <div className="mt-2 px-3 py-1.5 bg-red-950/20 text-red-500 rounded-lg text-xs font-medium w-fit border border-red-900/30 italic">
                                                    {story.progress || 'Fehler bei der Erstellung'}
                                                </div>
                                            ) : (
                                                <div className="mt-1 space-y-2">
                                                    {/* The Idea / Prompt */}
                                                    <div className="bg-background border border-slate-800 rounded-lg p-2 text-[11px] text-slate-500 italic">
                                                        <span className="font-bold uppercase tracking-wider text-[9px] block mb-0.5 text-slate-600 not-italic">Idee:</span>
                                                        {story.prompt}
                                                    </div>

                                                    {/* Full Synopsis */}
                                                    <p className="text-sm text-text font-serif leading-relaxed italic line-clamp-2 mt-2">{story.description}</p>

                                                    {/* Detailed Metadata Grid */}
                                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4 pt-4 border-t border-slate-800">
                                                        <div className="flex flex-col">
                                                            <span className="status-label text-slate-500">Genre</span>
                                                            <span className="text-[11px] text-primary font-semibold">{story.genre || '—'}</span>
                                                        </div>
                                                        <div className="flex flex-col">
                                                            <span className="status-label text-slate-500">Stil</span>
                                                            <span className="text-[11px] text-slate-300 font-medium truncate">{story.style.split(',')[0]}</span>
                                                        </div>
                                                        <div className="flex flex-col">
                                                            <span className="status-label text-slate-500">Stimme</span>
                                                            <span className="text-[11px] text-slate-300 font-medium truncate">{voiceName(story.voice_key)}</span>
                                                        </div>
                                                        <div className="flex flex-col">
                                                            <span className="status-label text-slate-500">Dauer</span>
                                                            <span className="text-[11px] text-slate-300 font-medium">{formatDuration(story.duration_seconds)}</span>
                                                        </div>
                                                    </div>

                                                    {/* Date & Info Row */}
                                                    <div className="flex items-center gap-3 text-[10px] text-slate-500 pt-1">
                                                        <span className="flex items-center gap-1">
                                                            <BookOpen className="w-3 h-3" />
                                                            {story.word_count ? `${story.word_count} Worte` : `${story.chapter_count} Kapitel`}
                                                        </span>
                                                        <span className="flex items-center gap-1">
                                                            <Calendar className="w-3 h-3" />
                                                            {formatDate(story.created_at)}
                                                        </span>
                                                        {user?.is_admin && archiveFilter === 'all' && (
                                                            <span className="flex items-center gap-1 border-l border-slate-800 pl-3">
                                                                <Users className="w-3 h-3" />
                                                                {story.user_id === user.id ? 'Von mir' : (story.user_email || story.user_id || 'Gast')}
                                                            </span>
                                                        )}
                                                        {story.is_public && (
                                                            <span className="flex items-center gap-1 border-l border-slate-800 pl-3 text-primary font-bold">
                                                                Öffentlich
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    <div className="mt-4 pt-3 border-t border-slate-800">
                                        <div className="grid grid-cols-2 gap-2 sm:flex sm:items-center sm:gap-4">
                                            <button
                                                onClick={() => handlePlay(story.id)}
                                                disabled={story.status !== 'done'}
                                                className="flex items-center justify-center sm:justify-start gap-1.5 px-3 py-2 bg-accent/20 sm:bg-transparent rounded-lg sm:rounded-none text-xs font-semibold text-primary hover:text-emerald-400 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                            >
                                                <Play className="w-3.5 h-3.5 fill-current" />
                                                Anhören
                                            </button>
                                            {user?.is_admin && story.user_id === user.id && (
                                                <button
                                                    onClick={async () => {
                                                        setIsPublicLoading(story.id);
                                                        try {
                                                            await toggleStoryVisibility(story.id, !story.is_public);
                                                            toast.success(story.is_public ? 'Story privatisiert' : 'Story veröffentlicht!');
                                                        } finally {
                                                            setIsPublicLoading(null);
                                                        }
                                                    }}
                                                    disabled={isPublicLoading === story.id}
                                                    className={`hidden sm:flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
                                                        story.is_public 
                                                        ? 'bg-accent/20 text-primary' 
                                                        : 'bg-slate-900 text-slate-500 hover:bg-slate-800'
                                                    }`}
                                                >
                                                    {isPublicLoading === story.id ? (
                                                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                    ) : (
                                                        <Users className="w-3.5 h-3.5" />
                                                    )}
                                                    {story.is_public ? 'Öffentlich' : 'Privat'}
                                                </button>
                                            )}
                                            
                                            {user?.is_admin && (
                                                <button
                                                    onClick={() => {
                                                        setRevoiceStoryId(story.id);
                                                        setSelectedVoice(story.voice_key || 'seraphina');
                                                    }}
                                                    disabled={story.status !== 'done' && story.status !== 'error'}
                                                    className="flex items-center justify-center sm:justify-start gap-1.5 px-3 py-2 bg-amber-950/20 sm:bg-transparent rounded-lg sm:rounded-none text-xs font-semibold text-amber-500 hover:text-amber-400 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                                >
                                                    <Mic className="w-3.5 h-3.5" />
                                                    Neu vertonen
                                                </button>
                                            )}
                                            {user?.is_admin && (
                                                <button
                                                    onClick={() => handleRegenerateImage(story.id)}
                                                    disabled={story.status !== 'done'}
                                                    className="flex items-center justify-center sm:justify-start gap-1.5 px-3 py-2 bg-slate-900 sm:bg-transparent rounded-lg sm:rounded-none text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors disabled:opacity-30"
                                                >
                                                    <ImageIcon className="w-3.5 h-3.5" />
                                                    Bild
                                                </button>
                                            )}
                                            <button
                                                onClick={() => setShowKindleModal(story.id)}
                                                disabled={(story.status !== 'done' && story.status !== 'error') || isExporting === story.id}
                                                className="flex items-center justify-center sm:justify-start gap-1.5 px-3 py-2 bg-emerald-950/20 sm:bg-transparent rounded-lg sm:rounded-none text-xs font-semibold text-emerald-500 hover:text-emerald-400 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                            >
                                                {isExporting === story.id ? (
                                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                ) : (
                                                    <Send className="w-3.5 h-3.5" />
                                                )}
                                                Kindle Export
                                            </button>
                                            <button
                                                onClick={() => {
                                                    setShowRemixModal(story.id);
                                                    setRemixType('improvement');
                                                    setRemixInstructions('');
                                                }}
                                                disabled={story.status !== 'done' || isRemixing}
                                                className="flex items-center justify-center sm:justify-start gap-1.5 px-3 py-2 bg-slate-900 sm:bg-transparent rounded-lg sm:rounded-none text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors disabled:opacity-30"
                                            >
                                                <RefreshCw className={`w-3.5 h-3.5 ${isRemixing && showRemixModal === story.id ? 'animate-spin' : ''}`} />
                                                Remix
                                            </button>
                                            {user?.is_admin && (
                                                <div className="flex items-center justify-center sm:justify-start">
                                                    <label className={`flex items-center gap-1.5 cursor-pointer group/toggle ${story.status !== 'done' ? 'opacity-30 cursor-not-allowed' : ''}`}>
                                                        <div className="relative">
                                                            <input
                                                                type="checkbox"
                                                                className="sr-only"
                                                                disabled={story.status !== 'done'}
                                                                checked={story.is_on_spotify}
                                                                onChange={(e) => handleSpotifyToggle(story.id, e.target.checked)}
                                                            />
                                                            <div className={`w-8 h-4.5 rounded-full transition-colors ${story.is_on_spotify ? 'bg-primary' : 'bg-slate-700'}`}></div>
                                                            <div className={`absolute top-0.5 left-0.5 w-3.5 h-3.5 bg-white rounded-full transition-transform ${story.is_on_spotify ? 'translate-x-3.5' : ''}`}></div>
                                                        </div>
                                                        <span className={`text-[10px] sm:text-xs font-semibold transition-colors ${story.is_on_spotify ? 'text-primary' : 'text-slate-500'}`}>
                                                            Spotify
                                                        </span>
                                                    </label>
                                                </div>
                                            )}
                                            <button
                                                onClick={() => {
                                                    const shareUrl = `${window.location.origin}${window.location.pathname}#/player/${story.id}`;
                                                    const text = `Schau mal, ich habe eine neue Geschichte erstellt: *${story.title}* 🌙✨\n\n${story.description}\n\nHör sie dir hier an:\n${shareUrl}`;
                                                    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
                                                }}
                                                disabled={story.status !== 'done'}
                                                className="flex items-center justify-center sm:justify-start gap-1.5 px-3 py-2 bg-green-950/20 sm:bg-transparent rounded-lg sm:rounded-none text-xs font-semibold text-green-500 hover:text-green-400 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                            >
                                                <MessageCircle className="w-3.5 h-3.5" />
                                                WhatsApp
                                            </button>
                                            {story.user_id === user?.id && (
                                                <button
                                                    onClick={() => handleDelete(story.id, story.title)}
                                                    className="flex items-center justify-center sm:justify-start gap-1.5 px-3 py-2 bg-red-950/20 sm:bg-transparent rounded-lg sm:rounded-none text-xs font-semibold text-red-500 hover:text-red-400 transition-colors"
                                                >
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                    Löschen
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Pagination Controls */}
            {totalStories > 30 && (
                <div className="mt-8 flex items-center justify-center gap-4">
                    <button
                        onClick={() => handlePageChange(currArchivePage - 1)}
                        disabled={currArchivePage <= 1}
                        className="p-2 rounded-xl border border-slate-200 text-slate-400 hover:text-[#2D5A4C] hover:border-[#D1FAE5] disabled:opacity-30 disabled:hover:text-slate-400 disabled:hover:border-slate-200 transition-all"
                    >
                        <ChevronLeft className="w-5 h-5" />
                    </button>
                    
                    <div className="text-sm font-semibold text-slate-500">
                        Seite <span className="text-[#2D5A4C]">{currArchivePage}</span> von {Math.ceil(totalStories / 30)}
                    </div>
                    
                    <button
                        onClick={() => handlePageChange(currArchivePage + 1)}
                        disabled={currArchivePage >= Math.ceil(totalStories / 30)}
                        className="p-2 rounded-xl border border-slate-200 text-slate-400 hover:text-[#2D5A4C] hover:border-[#D1FAE5] disabled:opacity-30 disabled:hover:text-slate-400 disabled:hover:border-slate-200 transition-all"
                    >
                        <ChevronRight className="w-5 h-5" />
                    </button>
                </div>
            )}

            {/* Re-voice Modal */}
            {revoiceStoryId && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
                    <div className="bg-surface rounded-3xl w-full max-w-md shadow-2xl border border-slate-800 overflow-hidden animate-in fade-in zoom-in duration-200">
                        <div className="p-6">
                            <div className="flex items-center justify-between mb-6">
                                <h2 className="text-xl font-bold text-text flex items-center gap-2">
                                    <Mic className="w-5 h-5 text-primary" />
                                    Neu vertonen
                                </h2>
                                <button
                                    onClick={() => { setRevoiceStoryId(null); setConfirmRevoice(false); }}
                                    className="p-2 text-slate-500 hover:text-slate-300 rounded-full hover:bg-slate-800"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            {!confirmRevoice ? (
                                <>
                                    <p className="text-sm text-slate-400 mb-4">Wähle eine neue Stimme für diese Geschichte:</p>
                                    <div className="grid grid-cols-1 gap-2 max-h-[300px] overflow-y-auto mb-6 pr-1 custom-scrollbar">
                                        {voices.filter(v => v.key !== 'none').map(v => (
                                            <div
                                                key={v.key}
                                                className={`p-3 rounded-xl transition-all border-2 cursor-pointer flex items-center justify-between ${selectedVoice === v.key
                                                    ? 'border-primary bg-accent/20 shadow-sm'
                                                    : 'border-slate-800 bg-surface hover:border-slate-700'
                                                    }`}
                                                onClick={() => setSelectedVoice(v.key)}
                                            >
                                                <div className="flex items-center gap-3">
                                                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${selectedVoice === v.key ? 'bg-primary/20 text-primary' : 'bg-slate-900 text-slate-700'}`}>
                                                        {v.gender === 'female' ? <Venus className="w-4 h-4" /> :
                                                            v.gender === 'male' ? <Mars className="w-4 h-4" /> : <Users className="w-4 h-4" />}
                                                    </div>
                                                    <div>
                                                        <div className={`text-xs font-bold ${selectedVoice === v.key ? 'text-text' : 'text-slate-400'}`}>
                                                            {voiceName(v.key)}
                                                        </div>
                                                        <div className={`text-[10px] ${selectedVoice === v.key ? 'text-primary' : 'text-slate-600'}`}>
                                                            {voiceDesc(v.key)}
                                                        </div>
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); handlePreviewVoice(v.key); }}
                                                    className={`w-7 h-7 rounded-full flex items-center justify-center transition-all shrink-0 ${previewVoice === v.key
                                                        ? 'bg-primary text-white'
                                                        : 'bg-slate-800 text-slate-500 hover:bg-slate-700'
                                                        }`}
                                                >
                                                    {previewVoice === v.key ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3 ml-0.5" />}
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                    <div className="flex gap-3">
                                        <button
                                            onClick={() => setRevoiceStoryId(null)}
                                            className="flex-1 px-4 py-3 border-2 border-slate-800 rounded-xl font-bold text-slate-500 hover:bg-surface transition-all"
                                        >
                                            Abbrechen
                                        </button>
                                        <button
                                            onClick={() => setConfirmRevoice(true)}
                                            className="btn-primary flex-1 px-4 py-3"
                                        >
                                            Weiter
                                        </button>
                                    </div>
                                </>
                            ) : (
                                <div className="text-center py-4">
                                    <div className="w-16 h-16 rounded-2xl bg-accent/20 text-primary flex items-center justify-center mx-auto mb-4">
                                        <Play className="w-8 h-8 fill-current" />
                                    </div>
                                    <h3 className="text-lg font-bold text-text mb-2">Bereit?</h3>
                                    <p className="text-sm text-slate-400 mb-8">
                                        Die Geschichte wird mit der Stimme <strong>{voiceName(selectedVoice)}</strong> neu vertont. Das Bestehende Audio wird ersetzt.
                                    </p>
                                    <div className="flex flex-col gap-3">
                                        <button
                                            onClick={async () => {
                                                if (!revoiceStoryId) return;
                                                setRevoicingId(revoiceStoryId);
                                                try {
                                                    await revoiceStory(revoiceStoryId, selectedVoice);
                                                    toast.success('Neuvertonung gestartet!');
                                                    setRevoiceStoryId(null);
                                                    setConfirmRevoice(false);
                                                } catch {
                                                    toast.error('Fehler beim Starten');
                                                } finally {
                                                    setRevoicingId(null);
                                                }
                                            }}
                                            disabled={revoicingId !== null}
                                            className="btn-primary w-full py-4"
                                        >
                                            {revoicingId ? <Loader2 className="w-5 h-5 animate-spin" /> : <Mic className="w-5 h-5" />}
                                            Jetzt starten
                                        </button>
                                        <button
                                            onClick={() => setConfirmRevoice(false)}
                                            disabled={revoicingId !== null}
                                            className="w-full py-3 text-sm font-bold text-slate-500 hover:text-slate-300 transition-colors"
                                        >
                                            Zurück zur Stimmenauswahl
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
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
                    <div className="bg-surface rounded-3xl w-full max-w-sm shadow-2xl border border-slate-800 overflow-hidden animate-in fade-in zoom-in duration-200">
                        <div className="p-6">
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-xl font-bold text-text flex items-center gap-2">
                                    <Send className="w-5 h-5 text-primary" />
                                    Kindle Export
                                </h2>
                                <button
                                    onClick={() => setShowKindleModal(null)}
                                    className="p-2 text-slate-500 hover:text-slate-300 rounded-full hover:bg-slate-800"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            <p className="text-sm text-slate-500 mb-6">
                                Gib deine Kindle E-Mail Adresse ein, um die Geschichte als E-Book zu senden.
                            </p>

                            <div className="space-y-4">
                                <div>
                                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1.5 ml-1">
                                        Kindle E-Mail Adresse
                                    </label>
                                    <input
                                        type="email"
                                        value={kindleEmail}
                                        onChange={(e) => setKindleEmail(e.target.value)}
                                        placeholder="beispiel@kindle.com"
                                        className="w-full px-4 py-3 bg-surface border-2 border-slate-800 rounded-xl focus:border-primary focus:ring-0 transition-all text-sm font-medium text-text"
                                    />
                                </div>

                                <button
                                    onClick={() => showKindleModal && handleKindleExport(showKindleModal)}
                                    disabled={isExporting === showKindleModal}
                                    className="w-full bg-primary text-white py-3 rounded-xl font-bold text-sm shadow-lg shadow-primary/20 hover:bg-emerald-600 transition-colors flex items-center justify-center gap-2"
                                >
                                    {isExporting === showKindleModal ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <Send className="w-4 h-4" />
                                    )}
                                    Jetzt senden
                                </button>

                                <p className="text-[10px] text-slate-500 text-center leading-relaxed">
                                    Stelle sicher, dass <span className="text-slate-300 font-semibold">dirk.proessel@gmail.com</span> in deinem Amazon-Konto als zugelassener Absender eingetragen ist.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Remix Modal */}
            {showRemixModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
                    <div className="bg-surface rounded-3xl w-full max-w-md shadow-2xl border border-slate-800 overflow-hidden animate-in fade-in zoom-in duration-200">
                        <div className="p-6">
                            <div className="flex items-center justify-between mb-6">
                                <h2 className="text-xl font-bold text-text flex items-center gap-2">
                                    <RefreshCw className="w-5 h-5 text-primary" />
                                    Geschichte Remixen
                                </h2>
                                <button
                                    onClick={() => setShowRemixModal(null)}
                                    className="p-2 text-slate-500 hover:text-slate-300 rounded-full hover:bg-slate-800"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                            
                            <div className="flex bg-background p-1 rounded-xl mb-6 border border-slate-800">
                                <button
                                    onClick={() => setRemixType('improvement')}
                                    className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${remixType === 'improvement' ? 'bg-primary text-white shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
                                >
                                    Verbessern
                                </button>
                                <button
                                    onClick={() => setRemixType('sequel')}
                                    className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${remixType === 'sequel' ? 'bg-primary text-white shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
                                >
                                    Fortsetzung (Sequel)
                                </button>
                            </div>

                            <p className="text-sm text-slate-400 mb-2">
                                {remixType === 'improvement' 
                                    ? 'Was soll an der Geschichte verbessert werden?' 
                                    : 'Worüber soll die Fortsetzung handeln?'}
                            </p>
                            
                            <textarea
                                value={remixInstructions}
                                onChange={(e) => setRemixInstructions(e.target.value)}
                                placeholder={remixType === 'improvement' 
                                    ? 'z.B. "Mehr Dialoge" oder "Ein anderes Ende"' 
                                    : 'z.B. "Sie finden einen Schatz" oder "Ein neuer Charakter erscheint"'}
                                className="w-full px-4 py-3 bg-background border-2 border-slate-800 rounded-xl text-sm focus:outline-none focus:border-primary transition-colors placeholder:text-slate-600 resize-none mb-6 text-text"
                                rows={4}
                            />

                            <button
                                onClick={() => handleRemix(showRemixModal)}
                                disabled={isRemixing}
                                className="btn-primary w-full py-4 text-base"
                            >
                                {isRemixing ? (
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                ) : (
                                    <Sparkles className="w-5 h-5" />
                                )}
                                {remixType === 'improvement' ? 'Version 2 erstellen' : 'Nächstes Kapitel schreiben'}
                            </button>

                            <button
                                onClick={() => showRemixModal && handleAdvancedRemix(showRemixModal)}
                                disabled={isRemixing}
                                className="w-full mt-3 bg-slate-800 hover:bg-slate-700 text-slate-300 py-3 rounded-xl font-bold text-xs transition-all flex items-center justify-center gap-2"
                            >
                                <Settings2 className="w-3.5 h-3.5" />
                                Mehr Optionen (Genre, Autor, Stimme ändern)
                            </button>
                        </div>
                    </div>
                </div>
            )}
            <audio ref={audioRef} className="hidden" />
        </div>
    );
}

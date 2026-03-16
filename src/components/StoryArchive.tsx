import { useStore } from '../store/useStore';
import { deleteStory, revoiceStory, getVoicePreviewUrl, exportStoryToKindle, getThumbUrl, regenerateStoryImage } from '../lib/api';
import { Play, Trash2, BookOpen, Loader2, Mic, X, Venus, Mars, Users, Pause, Send, ChevronLeft, ChevronRight, Image as ImageIcon, RefreshCw, Sparkles, Settings2, MessageCircle, Timer, Wand2, Edit, Feather, User as UserIcon } from 'lucide-react';
import toast from 'react-hot-toast';
import { useEffect, useState, useRef } from 'react';


import { voiceName, voiceDesc } from '../lib/voices';
import { authorName } from '../lib/authors';

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
    const [showToolbox, setShowToolbox] = useState<string | null>(null);
    const [expandedStories, setExpandedStories] = useState<Set<string>>(new Set());
    const audioRef = useRef<HTMLAudioElement>(null);

    const activeToolboxStory = showToolbox ? stories.find(s => s.id === showToolbox) : null;

    // Toolbox CSS Classes
    const sectionClass = "mb-6";
    const sectionTitleClass = "text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-slate-600 mb-3 ml-1";
    const listClass = "flex flex-col gap-2";
    const itemClass = "flex items-center gap-3 p-3 bg-slate-900/60 border border-slate-800/80 rounded-2xl transition-all active:scale-[0.98] hover:bg-primary/10 hover:border-primary/30 disabled:opacity-30 disabled:pointer-events-none w-full group/item";
    const itemLabelClass = "text-[13px] font-medium text-slate-300 group-hover/item:text-primary transition-colors";

    // Track if we have performed the initial check for "my" stories
    const [initialCheckDone, setInitialCheckDone] = useState(false);

    useEffect(() => {
        // First load with the initial filter
        loadStories(1);
    }, []);

    // Effect to switch to "public" if "my" is empty on first load
    useEffect(() => {
        if (!initialCheckDone && totalStories !== undefined && user) {
            if (archiveFilter === 'my' && totalMyStories === 0 && totalPublicStories > 0) {
                setArchiveFilter('public');
                loadStories(1);
            }
            setInitialCheckDone(true);
        }
    }, [totalMyStories, totalPublicStories, totalStories, initialCheckDone, archiveFilter, loadStories, setArchiveFilter, user]);


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


    const handlePlay = (id: string) => {
        setReaderOpen(true, id);
    };

    const toggleExpand = (id: string) => {
        setExpandedStories(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
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

    if (!user && archiveFilter === 'my') {
        return (
            <div className="p-4 sm:p-6 max-w-2xl mx-auto text-center py-20 animate-in fade-in duration-700">
                <div className="w-24 h-24 mx-auto bg-surface rounded-[2rem] flex items-center justify-center mb-6 shadow-sm border border-slate-800">
                    <UserIcon className="w-10 h-10 text-slate-700" />
                </div>
                <p className="text-slate-500 text-sm max-w-[280px] mx-auto leading-relaxed">
                    Melde dich an, um deine eigenen Geschichten zu speichern und zu verwalten.
                </p>
                <button 
                    onClick={() => setActiveView('login')}
                    className="btn-primary mt-8 px-8 mx-auto"
                >
                    Login
                </button>
            </div>
        );
    }

    return (
        <div className="p-4 sm:p-6 max-w-2xl mx-auto">
            {stories.length === 0 ? (
                <div className="text-center py-20 animate-in fade-in duration-700">
                    <div className="w-24 h-24 mx-auto bg-surface rounded-[2rem] flex items-center justify-center mb-6 shadow-sm border border-slate-800">
                        <BookOpen className="w-10 h-10 text-slate-700" />
                    </div>
                    <h2 className="font-serif text-2xl text-text mb-2 font-semibold">
                        {archiveFilter === 'public' ? 'Noch keine öffentlichen Geschichten' : 'Dein Archiv ist noch leer'}
                    </h2>
                    <p className="text-slate-500 text-sm max-w-[280px] mx-auto leading-relaxed">
                        {archiveFilter === 'public' 
                            ? 'Erstelle die erste öffentliche Geschichte im Labor!' 
                            : 'Hier werden deine literarischen Werke sicher aufbewahrt. Erstelle deine erste Geschichte im Labor!'}
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
                            className="bg-surface border border-slate-800 rounded-3xl p-5 hover:shadow-xl hover:shadow-primary/5 transition-all duration-300 group mb-6 relative overflow-hidden"
                        >
                            <div className="flex items-start gap-4">
                                {story.image_url ? (
                                    <div
                                        className="w-20 h-20 rounded-2xl overflow-hidden shrink-0 shadow-sm border border-slate-700 cursor-pointer"
                                        onClick={() => handlePlay(story.id)}
                                    >
                                        <img src={getThumbUrl(story.id, story.updated_at)} alt={story.title} className="w-full h-full object-cover grayscale-[20%]" />
                                    </div>
                                ) : (
                                    <div
                                        className="w-20 h-20 rounded-2xl bg-slate-900 flex items-center justify-center shrink-0 border border-slate-800 cursor-pointer"
                                        onClick={() => handlePlay(story.id)}
                                    >
                                        <BookOpen className="w-7 h-7 text-slate-700" />
                                    </div>
                                )}
                                <div className="flex-1 min-w-0">
                                    {/* Title & Top Metadata */}
                                    <div className="flex flex-col gap-1.5">
                                        <div className="flex items-center gap-2">
                                            {story.status === 'generating' && (!story.title || story.title.includes('Schreibe') || story.title.includes('Fortsetzung')) ? (
                                                <div className="font-serif text-lg font-semibold text-primary/40 animate-pulse flex flex-wrap gap-x-1">
                                                    {"Lorem ipsum dolor sit amet".split(" ").map((word, i) => (
                                                        <span key={i} className="flex gap-[1px]">
                                                            {word.split("").map((char, j) => (
                                                                <span key={j} className="inline-block animate-bounce" style={{ animationDelay: `${(i * 5 + j) * 80}ms`, animationDuration: '3s' }}>
                                                                    {char}
                                                                </span>
                                                            ))}
                                                        </span>
                                                    ))}
                                                </div>
                                            ) : (
                                                <h3 className="font-serif text-xl font-semibold text-text group-hover:text-primary transition-colors leading-tight cursor-pointer" onClick={() => story.status === 'done' && handlePlay(story.id)}>
                                                    {story.title}
                                                </h3>
                                            )}
                                        </div>
                                        
                                        <div className="flex gap-6 mb-1">
                                            <div className="flex flex-col">
                                                <span className="text-[8px] font-bold uppercase tracking-[0.2em] text-slate-500 mb-0.5">Genre</span>
                                                <span className="text-xs text-slate-300 font-bold">{story.genre || '—'}</span>
                                            </div>
                                            <div className="flex flex-col flex-1 min-w-0">
                                                <span className="text-[8px] font-bold uppercase tracking-[0.2em] text-slate-500 mb-0.5">Stil</span>
                                                <span className="text-xs text-slate-300 font-medium">
                                                    {story.style.split(',').map(id => authorName(id.trim())).join(', ')}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Moved Synopsis / Generating out of the side-by-side flex to align with left image edge */}
                            {story.status === 'generating' ? (
                                <div className="mt-4 space-y-2 w-full">
                                    <div className="flex justify-between items-end">
                                        <div className="flex items-center gap-2 text-primary text-xs font-semibold">
                                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                            {story.progress || 'Planung...'}
                                        </div>
                                        <span className="text-[10px] font-bold text-primary bg-accent/20 px-1.5 py-0.5 rounded-md">
                                            {story.progress_pct || 0}%
                                        </span>
                                    </div>
                                    <div className="w-full h-1.5 bg-accent/20 rounded-full overflow-hidden border border-primary/20">
                                        <div
                                            className="h-full bg-primary transition-all duration-1000 ease-out"
                                            style={{ width: `${story.progress_pct || 0}%` }}
                                        />
                                    </div>
                                </div>
                            ) : story.status === 'error' ? (
                                <div className="mt-4">
                                    <div className="px-3 py-2 bg-red-950/20 text-red-500 rounded-lg text-xs font-medium w-full border border-red-900/30 italic line-clamp-2 hover:line-clamp-none transition-all cursor-help" title={story.progress || 'Fehler bei der Erstellung'}>
                                        {story.progress || 'Fehler bei der Erstellung'}
                                    </div>
                                </div>
                            ) : (
                                <div className="mt-3">
                                    {/* The Idea / Prompt (Only in Library) */}
                                    {archiveFilter !== 'public' && (
                                        <div className="bg-background/40 border border-slate-800/50 rounded-xl p-3 text-[11px] text-slate-500 italic mb-3">
                                            <span className="font-bold uppercase tracking-[0.15em] text-[8px] block mb-1 text-slate-600 not-italic">Die Idee</span>
                                            {story.prompt}
                                        </div>
                                    )}

                                    {/* Full Synopsis */}
                                    <div className="relative">
                                        <p className={`text-[13px] text-text/90 font-serif leading-relaxed italic ${expandedStories.has(story.id) ? '' : 'line-clamp-3'}`}>
                                            {story.description}{!expandedStories.has(story.id) && story.description && story.description.length > 150 ? '...' : ''}
                                        </p>
                                        {!expandedStories.has(story.id) && story.description && story.description.length > 150 && (
                                            <div className="absolute bottom-0 right-0 h-5 pl-16 bg-gradient-to-l from-surface via-surface/90 to-transparent flex items-center">
                                                <button 
                                                    onClick={(e) => { e.stopPropagation(); toggleExpand(story.id); }}
                                                    className="text-[10px] font-bold text-primary hover:text-emerald-400 uppercase tracking-[0.1em] transition-colors"
                                                >
                                                    Mehr lesen
                                                </button>
                                            </div>
                                        )}
                                        {expandedStories.has(story.id) && (
                                            <button 
                                                onClick={(e) => { e.stopPropagation(); toggleExpand(story.id); }}
                                                className="text-[10px] font-bold text-primary hover:text-emerald-400 mt-1 uppercase tracking-wider transition-colors block"
                                            >
                                                Weniger anzeigen
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )}

                            {(story.status === 'done' || story.status === 'error') && (
                                <div className="mt-4">
                                    <div className="h-px bg-slate-800/50 w-full mb-3" />
                                    
                                    <div className="flex items-end justify-between px-2">
                                        {/* Left: Metadata */}
                                        <div className="flex flex-col gap-1 text-[11px] text-slate-500 font-medium">
                                            <span className="flex items-center gap-2">
                                                <BookOpen className="w-4 h-4 text-slate-600" />
                                                {(story.word_count && story.word_count > 0) ? `${story.word_count} Worte` : (story.chapter_count > 0 ? `${story.chapter_count} Kapitel` : 'Entwurf')}
                                            </span>
                                            {story.voice_key !== 'none' && (
                                                <span className="flex items-center gap-2">
                                                    <Timer className="w-4 h-4 text-slate-600" />
                                                    {story.duration_seconds ? formatDuration(story.duration_seconds) : '--:--'} Min ({voiceName(story.voice_key)})
                                                </span>
                                            )}
                                            {archiveFilter === 'public' && (
                                                <span className="flex items-center gap-2">
                                                    <Feather className="w-4 h-4 text-slate-600" />
                                                    {story.user_email || 'Anonym'}
                                                </span>
                                            )}
                                            {archiveFilter !== 'public' && story.is_public && (
                                                <div className="mt-1">
                                                    <span className="px-1.5 py-0.5 rounded-md bg-slate-800 border border-slate-700 text-[9px] font-bold text-slate-400 uppercase tracking-wider animate-in fade-in slide-in-from-left-1 duration-500">
                                                        Veröffentlicht
                                                    </span>
                                                </div>
                                            )}
                                        </div>

                                        {/* Center/Right Actions */}
                                        <div className="flex items-center gap-3">
                                            {/* Listen Button */}
                                            <button
                                                onClick={() => handlePlay(story.id)}
                                                className="w-12 h-12 bg-accent/20 border border-emerald-500/30 rounded-xl flex items-center justify-center text-primary hover:bg-accent/30 hover:border-emerald-500/50 transition-all active:scale-90 shadow-lg shadow-primary/10"
                                            >
                                                <Play className="w-6 h-6 fill-current" />
                                            </button>

                                            {/* Toolbox Button */}
                                            <button
                                                onClick={() => setShowToolbox(story.id)}
                                                className="w-12 h-12 bg-slate-900/80 border border-slate-700/50 rounded-xl flex items-center justify-center text-slate-400 hover:text-primary hover:border-primary/50 transition-all active:scale-90"
                                            >
                                                <Wand2 className="w-6 h-6" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}
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
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-md">
                    <div className="bg-surface/90 backdrop-blur-2xl rounded-[2.5rem] w-full max-w-md shadow-2xl border border-slate-800/50 overflow-hidden animate-in fade-in zoom-in duration-300">
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
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-md">
                    <div className="bg-surface/90 backdrop-blur-2xl rounded-[2.5rem] w-full max-w-sm shadow-2xl border border-slate-800/50 overflow-hidden animate-in fade-in zoom-in duration-300">
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
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-md">
                    <div className="bg-surface/90 backdrop-blur-2xl rounded-[2.5rem] w-full max-w-md shadow-2xl border border-slate-800/50 overflow-hidden animate-in fade-in zoom-in duration-300">
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

            {/* Toolbox Overlay */}
            {showToolbox && (
                <div className="fixed inset-0 z-[100] flex items-end justify-center bg-background/70 backdrop-blur-sm animate-in fade-in duration-500">
                    <div 
                        className="fixed inset-0" 
                        onClick={() => setShowToolbox(null)}
                    />
                    <div className="relative w-full max-w-md bg-surface/95 backdrop-blur-2xl border-t border-slate-800/50 rounded-t-[3rem] p-8 shadow-2xl animate-in slide-in-from-bottom duration-700 cubic-bezier(0.16, 1, 0.3, 1)">
                        <div className="flex flex-col items-center mb-8">
                            <div className="w-12 h-12 bg-primary/20 text-primary rounded-2xl flex items-center justify-center mb-3 shadow-lg shadow-primary/10">
                                <Wand2 className="w-7 h-7" />
                            </div>
                            <h2 className="text-sm font-mono uppercase tracking-[0.25em] text-slate-300 font-bold">
                                Werkzeugkasten
                            </h2>
                        </div>
                        <button
                            onClick={() => setShowToolbox(null)}
                            className="absolute top-6 right-6 p-2.5 bg-slate-900/80 text-slate-500 hover:text-white rounded-full hover:bg-slate-800 transition-all active:scale-95"
                        >
                            <X className="w-5 h-5" />
                        </button>

                        {activeToolboxStory && (
                            <div className="max-h-[70vh] overflow-y-auto custom-scrollbar pr-1 pb-4">
                                {/* Remix Labor */}
                                <div className={sectionClass}>
                                    <h3 className={sectionTitleClass}>Remix Labor</h3>
                                    <div className={listClass}>
                                        <button 
                                            onClick={() => { 
                                                setShowRemixModal(activeToolboxStory.id); 
                                                setRemixType('improvement'); 
                                                setShowToolbox(null); 
                                            }}
                                            className={itemClass}
                                        >
                                            <Edit className="w-4 h-4 text-emerald-400 shrink-0" />
                                            <span className={itemLabelClass}>Anpassen</span>
                                        </button>
                                        <button 
                                            onClick={() => { 
                                                setShowRemixModal(activeToolboxStory.id); 
                                                setRemixType('sequel'); 
                                                setShowToolbox(null); 
                                            }}
                                            className={itemClass}
                                        >
                                            <Sparkles className="w-4 h-4 text-emerald-500 shrink-0" />
                                            <span className={itemLabelClass}>Fortsetzen</span>
                                        </button>
                                    </div>
                                </div>

                                {/* Sichtbarkeit & Versand */}
                                <div className={sectionClass}>
                                    <h3 className={sectionTitleClass}>Sichtbarkeit & Versand</h3>
                                    <div className={listClass}>
                                        {/* Publish Toggle - Only for own stories in library */}
                                        {archiveFilter !== 'public' && activeToolboxStory.user_id === user?.id && (
                                            <div className={`${itemClass} justify-between px-3`}>
                                                <div className="flex items-center gap-3">
                                                    <Sparkles className="w-4 h-4 text-primary shrink-0" />
                                                    <div className="flex flex-col">
                                                        <span className={itemLabelClass}>Veröffentlichen</span>
                                                        <span className="text-[10px] text-slate-500">
                                                            {activeToolboxStory.is_public ? 'In "Erkunden" sichtbar' : 'Nur für Dich sichtbar'}
                                                        </span>
                                                    </div>
                                                </div>
                                                
                                                <button 
                                                    onClick={async () => {
                                                        const targetId = activeToolboxStory.id;
                                                        setIsPublicLoading(targetId);
                                                        try {
                                                            await toggleStoryVisibility(targetId, !activeToolboxStory.is_public);
                                                            toast.success(activeToolboxStory.is_public ? 'Story privatisiert' : 'Story veröffentlicht!');
                                                        } finally {
                                                            setIsPublicLoading(null);
                                                        }
                                                    }}
                                                    disabled={isPublicLoading === activeToolboxStory.id}
                                                    className={`relative w-10 h-5 rounded-full transition-all duration-300 flex items-center p-0.5 ${
                                                        isPublicLoading === activeToolboxStory.id ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                                                    } ${
                                                        activeToolboxStory.is_public 
                                                            ? 'bg-[#00F5D4] shadow-[0_0_12px_rgba(0,245,212,0.4)]' 
                                                            : 'bg-slate-800'
                                                    }`}
                                                >
                                                    <div className={`w-4 h-4 bg-[#0a0f1d] rounded-full shadow-sm transition-transform duration-300 transform ${
                                                        activeToolboxStory.is_public ? 'translate-x-5' : 'translate-x-0'
                                                    } flex items-center justify-center`}>
                                                        {isPublicLoading === activeToolboxStory.id && (
                                                            <Loader2 className="w-2.5 h-2.5 animate-spin text-[#00F5D4]" />
                                                        )}
                                                    </div>
                                                </button>
                                            </div>
                                        )}

                                        <button 
                                            onClick={() => {
                                                const shareUrl = `${window.location.origin}${window.location.pathname}#/Story/${activeToolboxStory.id}`;
                                                const text = `Schau mal, ich habe eine neue Geschichte erstellt: *${activeToolboxStory.title}* 🌙✨\n\n${activeToolboxStory.description}\n\nHör sie dir hier an:\n${shareUrl}`;
                                                window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
                                                setShowToolbox(null);
                                            }}
                                            className={itemClass}
                                        >
                                            <MessageCircle className="w-4 h-4 text-green-500 shrink-0" />
                                            <span className={itemLabelClass}>WhatsApp</span>
                                        </button>

                                        <button 
                                            onClick={() => { setShowKindleModal(activeToolboxStory.id); setShowToolbox(null); }}
                                            className={itemClass}
                                        >
                                            <Send className="w-4 h-4 text-blue-400 shrink-0" />
                                            <span className={itemLabelClass}>An Kindle</span>
                                        </button>
                                    </div>
                                </div>

                                {/* Werkzeuge */}
                                <div className={sectionClass}>
                                    <h3 className={sectionTitleClass}>Werkzeuge</h3>
                                    <div className={listClass}>
                                        {/* Admin/Own only Tools */}
                                        {archiveFilter !== 'public' && (activeToolboxStory.user_id === user?.id || user?.is_admin) && (
                                            <>
                                                <button 
                                                    onClick={() => { 
                                                        setRevoiceStoryId(activeToolboxStory.id); 
                                                        setSelectedVoice(activeToolboxStory.voice_key || 'seraphina'); 
                                                        setShowToolbox(null); 
                                                    }}
                                                    className={itemClass}
                                                >
                                                    <Mic className="w-4 h-4 text-amber-500 shrink-0" />
                                                    <span className={itemLabelClass}>Neu vertonen</span>
                                                </button>
                                                <button 
                                                    onClick={() => { handleRegenerateImage(activeToolboxStory.id); setShowToolbox(null); }}
                                                    className={itemClass}
                                                >
                                                    <ImageIcon className="w-4 h-4 text-indigo-400 shrink-0" />
                                                    <span className={itemLabelClass}>Neues Bild</span>
                                                </button>
                                            </>
                                        )}

                                        {user?.is_admin && (
                                            <div className={`${itemClass} justify-between px-3`}>
                                                <div className="flex items-center gap-3">
                                                    <Play className="w-4 h-4 text-[#1DB954] shrink-0" />
                                                    <span className={itemLabelClass}>Spotify</span>
                                                </div>
                                                <button 
                                                    onClick={() => {
                                                        handleSpotifyToggle(activeToolboxStory.id, !activeToolboxStory.is_on_spotify);
                                                        setShowToolbox(null);
                                                    }}
                                                    className={`relative w-10 h-5 rounded-full transition-all duration-300 flex items-center p-0.5 cursor-pointer ${
                                                        activeToolboxStory.is_on_spotify 
                                                            ? 'bg-[#1DB954] shadow-[0_0_12px_rgba(29,185,84,0.3)]' 
                                                            : 'bg-slate-800'
                                                    }`}
                                                >
                                                    <div className={`w-4 h-4 bg-[#0a0f1d] rounded-full shadow-sm transition-transform duration-300 transform ${
                                                        activeToolboxStory.is_on_spotify ? 'translate-x-5' : 'translate-x-0'
                                                    }`} />
                                                </button>
                                            </div>
                                        )}

                                        {activeToolboxStory.user_id === user?.id && (
                                            <button 
                                                onClick={() => { handleDelete(activeToolboxStory.id, activeToolboxStory.title); setShowToolbox(null); }}
                                                className={itemClass}
                                            >
                                                <Trash2 className="w-4 h-4 text-red-500/70 shrink-0" />
                                                <span className={itemLabelClass}>Löschen</span>
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
            <audio ref={audioRef} className="hidden" />
        </div>
    );
}

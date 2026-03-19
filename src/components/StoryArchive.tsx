import { useStore } from '../store/useStore';
import { createPortal } from 'react-dom';
import { getVoicePreviewUrl, exportStoryToKindle, getThumbUrl, getImageUrl, regenerateStoryImage } from '../lib/api';
import { Play, Trash2, Heart, BookOpen, Loader2, Mic, X, Venus, Mars, Users, Pause, Send, Image as ImageIcon, RefreshCw, Sparkles, Settings2, MessageCircle, Timer, Wand2, Edit, Feather, User as UserIcon, Search, ChevronLeft, ChevronRight, ArrowLeft } from 'lucide-react';
import toast from 'react-hot-toast';
import { useEffect, useState, useRef } from 'react';
import ConfirmModal from './ConfirmModal';


import { voiceName, voiceDesc } from '../lib/voices';
import { authorName } from '../lib/authors';
import { GENRES } from './StoryCreator';

function HeroSection({ story, onPlay, onFavorite }: { story: any, onPlay: (id: string) => void, onFavorite: (id: string) => void }) {
    if (!story) return null;
    return (
        <div className="relative w-full h-[320px] sm:h-[400px] lg:h-[500px] mb-8 rounded-[2.5rem] overflow-hidden group cursor-pointer border border-slate-800 shadow-2xl animate-in fade-in zoom-in-95 duration-500" onClick={() => onPlay(story.id)}>
            <div className="absolute inset-0 overflow-hidden">
                <img 
                    src={getImageUrl(story.id, story.updated_at)} 
                    alt={story.title} 
                    className="w-full h-full object-cover grayscale-[10%] scale-110 group-hover:scale-[1.15] transition-transform duration-700" 
                />
            </div>
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-transparent" />
            
            <div className="absolute bottom-0 left-0 right-0 p-6 sm:p-10">
                <div className="flex items-center gap-2 mb-3">
                    <span className="px-2 py-0.5 bg-primary/20 border border-primary/30 text-primary text-xs font-bold uppercase tracking-wider rounded-md backdrop-blur-md">
                        storyja-Empfehlung
                    </span>
                </div>
                <h2 className="text-3xl sm:text-4xl font-bold text-white mb-3 leading-tight drop-shadow-lg">
                    {story.title}
                </h2>
                <p className="text-sm text-slate-300 line-clamp-2 max-w-lg mb-8 leading-relaxed italic drop-shadow-sm">
                    {story.description}
                </p>
                
                <div className="flex items-center gap-4">
                    <button 
                        onClick={(e) => { e.stopPropagation(); onPlay(story.id); }}
                        className="btn-primary px-8 py-3 shadow-2xl shadow-primary/20 text-md"
                    >
                        <Play className="w-5 h-5 fill-current" />
                        Jetzt hören
                    </button>
                    <button 
                        onClick={(e) => { e.stopPropagation(); onFavorite(story.id); }}
                        className={`w-12 h-12 rounded-2xl flex items-center justify-center border backdrop-blur-md transition-all active:scale-90 ${
                            story.is_favorite 
                            ? 'bg-red-500/10 border-red-500/50 text-red-500 shadow-lg shadow-red-500/10' 
                            : 'bg-white/5 border-white/10 text-white hover:bg-white/10'
                        }`}
                    >
                        <Heart className={`w-6 h-6 ${story.is_favorite ? 'fill-current' : ''}`} />
                    </button>
                </div>
            </div>
        </div>
    );
}

function CollectionRow({ title, stories, onPlay, onFavorite, onToolbox }: { title: string, stories: any[], onPlay: (id: string) => void, onFavorite: (id: string) => void, onToolbox: (id: string) => void }) {
    if (stories.length === 0) return null;
    const scrollRef = useRef<HTMLDivElement>(null);
    const [showLeft, setShowLeft] = useState(false);
    const [showRight, setShowRight] = useState(true);

    const handleScroll = () => {
        if (scrollRef.current) {
            const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current;
            setShowLeft(scrollLeft > 20);
            setShowRight(scrollLeft < scrollWidth - clientWidth - 20);
        }
    };

    return (
        <div className="mb-10 last:mb-0">
            <h3 className="text-xs font-bold uppercase tracking-[0.25em] text-slate-500 mb-5 ml-1 flex items-center gap-2.5">
                <Sparkles className="w-4 h-4 text-primary" />
                {title}
            </h3>
            <div className="relative group/row">
                <div 
                    ref={scrollRef}
                    onScroll={handleScroll}
                    className="flex gap-4 overflow-x-auto no-scrollbar scroll-smooth px-1 pb-6"
                >
                    {stories.map(s => (
                        <div 
                            key={s.id} 
                            className="shrink-0 w-[180px] sm:w-[240px]"
                        >
                            <FlipStoryCard 
                                story={s} 
                                onPlay={onPlay} 
                                onFavorite={onFavorite} 
                                onToolbox={onToolbox}
                            />
                        </div>
                    ))}
                    {/* Ghost card for spacing */}
                    <div className="shrink-0 w-8" />
                </div>
                
                {/* Scroll Buttons for Desktop */}
                {showLeft && (
                    <button 
                        onClick={() => scrollRef.current?.scrollBy({ left: -400, behavior: 'smooth' })}
                        className="absolute left-0 top-[40%] -translate-y-1/2 -ml-5 w-11 h-11 rounded-full bg-slate-900/90 border border-slate-800 text-slate-400 hidden md:flex items-center justify-center hover:text-white hover:bg-slate-800 transition-all shadow-xl backdrop-blur-md z-10"
                    >
                        <ChevronLeft className="w-6 h-6" />
                    </button>
                )}
                {showRight && (
                    <button 
                        onClick={() => scrollRef.current?.scrollBy({ left: 400, behavior: 'smooth' })}
                        className="absolute right-0 top-[40%] -translate-y-1/2 -mr-5 w-11 h-11 rounded-full bg-slate-900/90 border border-slate-800 text-slate-400 hidden md:flex items-center justify-center hover:text-white hover:bg-slate-800 transition-all shadow-xl backdrop-blur-md z-10"
                    >
                        <ChevronRight className="w-6 h-6" />
                    </button>
                )}
            </div>
        </div>
    );
}

function FlipStoryCard({ story, onPlay, onFavorite, onToolbox }: { story: any, onPlay: (id: string) => void, onFavorite: (id: string) => void, onToolbox: (id: string) => void }) {
    const [isFlipped, setIsFlipped] = useState(false);
    if (!story) return null;

    return (
        <div 
            className="relative aspect-[3/4] group perspective-1000 cursor-pointer"
            onClick={() => setIsFlipped(!isFlipped)}
        >
            <div className={`relative w-full h-full transition-all duration-700 preserve-3d ${isFlipped ? 'rotate-y-180' : ''}`}>
                
                {/* Front Side */}
                <div className={`absolute inset-0 backface-hidden rounded-3xl overflow-hidden border border-slate-800 shadow-xl group-hover:shadow-primary/10 transition-shadow ${isFlipped ? 'pointer-events-none' : ''}`}>
                    <img 
                        src={getThumbUrl(story.id, story.updated_at)} 
                        alt={story.title} 
                        className="w-full h-full object-cover grayscale-[10%] scale-105 group-hover:scale-110 transition-transform duration-700" 
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-slate-950/20 to-transparent opacity-80" />
                    
                    {/* Top Actions */}
                    <div className="absolute top-3 left-3 right-3 z-10 flex items-center justify-between">
                        {/* Play Button */}
                        <button
                            onClick={(e) => { e.stopPropagation(); onPlay(story.id); }}
                            className="w-9 h-9 bg-primary text-white rounded-xl flex items-center justify-center shadow-lg active:scale-95 transition-all cursor-pointer"
                        >
                            <Play className="w-4 h-4 fill-current ml-0.5" />
                        </button>

                        {/* Grouped Actions (Heart & Toolbox) */}
                        <div className="flex items-center bg-slate-900/40 backdrop-blur-md rounded-xl border border-white/10 p-0.5">
                            {/* Heart Toggle */}
                            <button
                                onClick={(e) => { e.stopPropagation(); onFavorite(story.id); }}
                                className={`w-9 h-9 rounded-lg flex items-center justify-center transition-all active:scale-95 cursor-pointer ${
                                    story.is_favorite 
                                    ? 'text-red-500 bg-red-500/10' 
                                    : 'text-white/70 hover:text-white hover:bg-white/5'
                                }`}
                            >
                                <Heart className={`w-4 h-4 ${story.is_favorite ? 'fill-current' : ''}`} />
                            </button>
                            
                            {/* Divider if both could be present */}
                            <div className="w-px h-4 bg-white/10 mx-0.5" />

                            {/* Toolbox Button */}
                            <button
                                onClick={(e) => { e.stopPropagation(); onToolbox(story.id); }}
                                className="w-9 h-9 rounded-lg flex items-center justify-center text-white/70 hover:text-white hover:bg-white/5 transition-all active:scale-95 cursor-pointer"
                            >
                                <Wand2 className="w-4 h-4" />
                            </button>
                        </div>
                    </div>

                    <div className="absolute bottom-4 left-4 right-4">
                        <div className="flex items-center gap-1.5 mb-1">
                            <div className="text-xs font-bold text-primary uppercase tracking-wider">{story.genre}</div>
                            {story.voice_key !== 'none' && (
                                <Mic className="w-3 h-3 text-primary/70" strokeWidth={3} />
                            )}
                        </div>
                        <h4 className="text-[14px] font-bold text-white line-clamp-3 leading-tight drop-shadow-md">
                            {story.title}
                        </h4>
                    </div>
                </div>

                <div className={`absolute inset-0 backface-hidden rotate-y-180 rounded-3xl overflow-hidden border border-slate-700/50 bg-slate-900/95 backdrop-blur-xl p-3 flex flex-col shadow-2xl ${!isFlipped ? 'pointer-events-none' : ''}`}>
                    <div className="flex-1 min-h-0 no-scrollbar overflow-y-auto">
                        <p className="text-[12px] text-slate-300 font-normal leading-[1.4] tracking-tight">
                            {story.description}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}


export default function StoryArchive() {
    const { 
        stories, loadStories, setActiveView, 
        toggleStoryVisibility, user, archiveFilter, setArchiveFilter,
        totalStories, totalMyStories, totalPublicStories,
        voices, revoiceStoryId, setRevoiceStoryId,
        updateStorySpotify, startGeneration,
        setGeneratorPrompt, setGeneratorGenre, setGeneratorAuthors,
        setGeneratorMinutes, setGeneratorVoice, setGeneratorRemix,
        setReaderOpen,
        toggleFavorite,
        deleteStory,
        loadMoreStories, hasMore, isLoading,
        archiveGenre, archiveSearch, setArchiveGenre, setArchiveSearch, toggleArchiveGenre,
        revoiceStory, availableGenres
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
    const [deleteConfirm, setDeleteConfirm] = useState<{ id: string, title: string } | null>(null);
    const audioRef = useRef<HTMLAudioElement>(null);
    
    // Discovery Collections
    const [fairytales, setFairytales] = useState<any[]>([]);
    const [adventure, setAdventure] = useState<any[]>([]);
    const [sleepStories, setSleepStories] = useState<any[]>([]);
    const [scifi, setScifi] = useState<any[]>([]);
    
    // Filter UI state
    const [isScrolled, setIsScrolled] = useState(false);
    const [filterLevel, setFilterLevel] = useState<'main' | 'search' | 'genre'>('main');
    const [searchValue, setSearchValue] = useState(archiveSearch || '');
    const genreScrollRef = useRef<HTMLDivElement>(null);
    const [showLeftFade, setShowLeftFade] = useState(false);
    const [showRightFade, setShowRightFade] = useState(true);

    const activeToolboxStory = showToolbox ? stories.find(s => s.id === showToolbox) : null;

    // Toolbox CSS Classes
    const sectionClass = "mb-6";
    const sectionTitleClass = "text-xs font-bold uppercase tracking-widest text-slate-600 mb-3 ml-1";
    const listClass = "grid grid-cols-2 gap-2";
    const itemClass = "flex items-center gap-2.5 p-2.5 bg-slate-900/60 border border-slate-800/80 rounded-xl transition-all active:scale-[0.98] hover:bg-primary/10 hover:border-primary/30 disabled:opacity-30 disabled:pointer-events-none w-full group/item";
    const itemLabelClass = "text-[12px] font-medium text-slate-300 group-hover/item:text-primary transition-colors truncate";

    // Track if we have performed the initial check for "my" stories
    const [initialCheckDone, setInitialCheckDone] = useState(false);

    useEffect(() => {
        // First load with the initial filter
        loadStories(1);
        
        // If we are in discover mode, pre-fetch rows
        if (archiveFilter === 'public') {
            loadCollections();
        }
    }, [archiveFilter]);

    const loadCollections = async () => {
        const { fetchStories } = await import('../lib/api');
        try {
            const [ft, adv, sleep, sf] = await Promise.all([
                fetchStories({ page: 1, pageSize: 8, filter: 'public', genre: ['Märchen'] }),
                fetchStories({ page: 1, pageSize: 8, filter: 'public', genre: ['Abenteuer'] }),
                fetchStories({ page: 1, pageSize: 8, filter: 'public', genre: ['Gute Nacht'] }),
                fetchStories({ page: 1, pageSize: 8, filter: 'public', genre: ['Science-Fiction'] }),
            ]);
            setFairytales(ft.stories);
            setAdventure(adv.stories);
            setSleepStories(sleep.stories);
            setScifi(sf.stories);
        } catch (err) {
            console.error("Failed to load collections", err);
        }
    };


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

    // Handle initial genres scroll check
    useEffect(() => {
        const handleScroll = () => {
            if (genreScrollRef.current) {
                const { scrollLeft, scrollWidth, clientWidth } = genreScrollRef.current;
                setShowLeftFade(scrollLeft > 10);
                setShowRightFade(scrollLeft < scrollWidth - clientWidth - 10);
            }
        };
        const el = genreScrollRef.current;
        if (el) {
            el.addEventListener('scroll', handleScroll);
            handleScroll(); // Initial
        }
        return () => el?.removeEventListener('scroll', handleScroll);
    }, [filterLevel]);

    // Handle Search Debounce
    useEffect(() => {
        const timer = setTimeout(() => {
            if (searchValue !== (archiveSearch || '')) {
                setArchiveSearch(searchValue || null);
                loadStories(1);
            }
        }, 500);
        return () => clearTimeout(timer);
    }, [searchValue, archiveSearch, setArchiveSearch, loadStories]);

    const handleGenreSelect = (genre: string | null) => {
        if (genre === null) {
            setArchiveGenre([]);
        } else {
            toggleArchiveGenre(genre);
        }
        setArchiveSearch(null);
        setSearchValue('');
        loadStories(1);
    };


    const observerTarget = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const observer = new IntersectionObserver(
            entries => {
                if (entries[0].isIntersecting && hasMore && !isLoading) {
                    loadMoreStories();
                }
            },
            { threshold: 0.1, rootMargin: '100px' }
        );

        if (observerTarget.current) {
            observer.observe(observerTarget.current);
        }

        return () => observer.disconnect();
    }, [hasMore, isLoading, loadMoreStories]);

    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 0);
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);


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
        setDeleteConfirm({ id, title });
    };

    const confirmDelete = async () => {
        if (!deleteConfirm) return;
        const { id } = deleteConfirm;
        try {
            await deleteStory(id);
            toast.success('Geschichte gelöscht');
        } catch {
            toast.error('Fehler beim Löschen');
        } finally {
            setDeleteConfirm(null);
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
        <div className="px-3 py-4 sm:p-6 w-full mx-auto">
            {/* Desktop Filters (Portalled to Sidebar) */}
            {typeof document !== 'undefined' && document.getElementById('desktop-context-sidebar') && createPortal(
                <div className="hidden lg:block space-y-8">
                    {/* Search Section */}
                    <div>
                        <div className="mb-3 flex items-center gap-2">
                            <h3 className="status-label text-primary">Suchen</h3>
                            <div className="h-px flex-1 bg-slate-800/50" />
                        </div>
                        <div className="relative group">
                            <input 
                                type="text"
                                value={searchValue}
                                onChange={(e) => setSearchValue(e.target.value)}
                                placeholder="Titel oder Thema..."
                                className="w-full pl-10 pr-4 py-3 bg-surface border-2 border-slate-800 rounded-2xl text-sm focus:outline-none focus:border-primary transition-all placeholder:text-slate-600"
                            />
                            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600 group-focus-within:text-primary transition-colors" />
                            {searchValue && (
                                <button 
                                    onClick={() => { setSearchValue(''); setArchiveSearch(null); }}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-600 hover:text-white"
                                >
                                    <X className="w-3.5 h-3.5" />
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Genre Section (Vertical) */}
                    <div>
                        <div className="mb-3 flex items-center gap-2">
                            <h3 className="status-label text-primary">Genre</h3>
                            <div className="h-px flex-1 bg-slate-800/50" />
                        </div>
                        <div className="space-y-1.5 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                            <button
                                onClick={() => handleGenreSelect(null)}
                                className={`w-full flex items-center justify-between px-4 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all border-2 ${
                                    archiveGenre.length === 0
                                        ? 'bg-primary/10 border-primary text-primary' 
                                        : 'bg-slate-900 border-slate-800 text-slate-500 hover:border-slate-700'
                                }`}
                            >
                                <span>Alle</span>
                                {archiveGenre.length === 0 && <div className="w-1.5 h-1.5 rounded-full bg-primary" />}
                            </button>
                            {GENRES.filter(g => availableGenres.includes(g.value)).map(g => (
                                <button
                                    key={g.value}
                                    onClick={() => handleGenreSelect(g.value)}
                                    className={`w-full flex items-center justify-between px-4 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all border-2 ${
                                        archiveGenre.includes(g.value)
                                            ? 'bg-primary/10 border-primary text-primary' 
                                            : 'bg-slate-900 border-slate-800 text-slate-500 hover:border-slate-700'
                                    }`}
                                >
                                    <span className="truncate">{g.label}</span>
                                    {archiveGenre.includes(g.value) && <div className="w-1.5 h-1.5 rounded-full bg-primary" />}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Stats or extra info could go here */}
                    <div className="pt-8 border-t border-slate-800/30">
                        <div className="flex items-center justify-between text-xs uppercase font-bold tracking-widest text-slate-600">
                            <span>Total</span>
                            <span>{totalPublicStories} Geschichten</span>
                        </div>
                    </div>
                </div>,
                document.getElementById('desktop-context-sidebar')!
            )}

            {/* Mobile Filter Bar (Hidden on Desktop) */}
            <div className={`lg:hidden mb-4 sticky top-0 z-30 bg-background/80 backdrop-blur-md pb-2 -mx-3 px-3 sm:-mx-6 sm:px-6 transition-all duration-300 ${isScrolled ? 'border-b border-primary/20 shadow-sm' : 'border-transparent'}`}>
                <div className="relative flex items-center h-10 bg-surface/50 border border-slate-800 rounded-2xl overflow-hidden transition-all duration-300">
                    
                    {filterLevel === 'main' && (
                        <div className="flex-1 flex w-full items-center px-2 gap-2 animate-in fade-in zoom-in-95 duration-200">
                            <button 
                                onClick={() => setFilterLevel('search')}
                                className={`flex items-center gap-2 px-3 h-7 rounded-xl text-sm font-medium transition-colors ${
                                    archiveSearch 
                                        ? 'bg-primary/20 text-primary border border-primary/20' 
                                        : 'bg-slate-800/50 hover:bg-slate-800 text-slate-300 border border-transparent'
                                }`}
                            >
                                <Search className="w-3.5 h-3.5" />
                                <span className="truncate max-w-[120px]">{archiveSearch ? `"${archiveSearch}"` : 'Suchen'}</span>
                                {archiveSearch && (
                                    <div 
                                        onClick={(e) => { e.stopPropagation(); setArchiveSearch(null); setSearchValue(''); }}
                                        className="ml-1 -mr-1 p-0.5 hover:bg-slate-900/50 rounded-full"
                                    >
                                        <X className="w-3.5 h-3.5" />
                                    </div>
                                )}
                            </button>
                            
                            {/* Genre Level 1 */}
                            <div className="relative group">
                                <button 
                                    onClick={() => setFilterLevel('genre')}
                                    className={`pl-3 pr-3 py-1.5 rounded-full text-[13px] font-bold tracking-wide transition-all border flex items-center gap-1.5 shadow-sm active:scale-95 ${
                                        archiveGenre.length > 0
                                            ? 'bg-primary/20 border-primary/40 text-primary hover:bg-primary/30' 
                                            : 'bg-slate-900/50 border-slate-800 text-slate-400 hover:text-slate-300 hover:bg-slate-800 hover:border-slate-700'
                                    }`}
                                >
                                    <BookOpen className="w-3.5 h-3.5" />
                                    {archiveGenre.length > 0 
                                        ? (archiveGenre.length === 1 ? archiveGenre[0] : `${archiveGenre.length} Genres`) 
                                        : 'Genre'}
                                </button>
                                {archiveGenre.length > 0 && (
                                    <button 
                                        onClick={(e) => { e.stopPropagation(); setArchiveGenre([]); loadStories(1); }}
                                        className="absolute -top-1 -right-1 p-0.5 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded-full transition-colors border border-slate-700"
                                    >
                                        <X className="w-2.5 h-2.5" />
                                    </button>
                                )}
                            </div>
                            
                            {/* Placeholder for future extensible filters */}
                            {/* 
                            <button className="flex items-center gap-2 px-3 h-7 rounded-xl text-sm font-medium transition-colors bg-slate-800/50 hover:bg-slate-800 text-slate-400 border border-transparent border-dashed">
                                <Feather className="w-3.5 h-3.5" />
                                <span>Autor</span>
                            </button>
                            */}
                        </div>
                    )}

                    {filterLevel === 'search' && (
                        <div className="flex-1 flex w-full items-center px-3 animate-in fade-in slide-in-from-left-2 duration-200">
                            <button 
                                onClick={() => setFilterLevel('main')}
                                className="p-1.5 -ml-1.5 mr-1 text-slate-500 hover:text-slate-300 transition-colors rounded-lg hover:bg-slate-800/50"
                            >
                                <ArrowLeft className="w-5 h-5" />
                            </button>
                            <input 
                                type="text"
                                value={searchValue}
                                onChange={(e) => setSearchValue(e.target.value)}
                                placeholder="Titel oder Synopsis suchen..."
                                autoFocus
                                className="flex-1 bg-transparent border-0 border-none outline-none focus:outline-none focus:ring-0 text-[15px] text-text placeholder:text-slate-500 px-2 min-w-0"
                            />
                            {searchValue && (
                                <button 
                                    onClick={() => { setSearchValue(''); setArchiveSearch(null); }}
                                    className="p-1.5 -mr-1.5 text-slate-500 hover:text-slate-300 transition-colors rounded-lg hover:bg-slate-800/50"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            )}
                        </div>
                    )}

                    {filterLevel === 'genre' && (
                        <div className="flex-1 flex items-center w-full pl-3 animate-in fade-in slide-in-from-left-2 duration-200 relative">
                            <button 
                                onClick={() => setFilterLevel('main')}
                                className="p-1.5 -ml-1.5 mr-2 text-slate-500 hover:text-slate-300 transition-colors rounded-lg hover:bg-slate-800/50 shrink-0 relative z-20"
                            >
                                <ArrowLeft className="w-5 h-5" />
                            </button>

                            <div className="relative flex-1 overflow-hidden h-full flex items-center pr-2">
                                {/* Desktop Scroll Button Left */}
                                {showLeftFade && (
                                    <div className="absolute left-0 top-0 bottom-0 flex items-center bg-gradient-to-r from-surface via-surface to-transparent pr-4 z-10 pointer-events-none">
                                        <button 
                                            onClick={(e) => {
                                                e.preventDefault();
                                                if (genreScrollRef.current) {
                                                    genreScrollRef.current.scrollBy({ left: -200, behavior: 'smooth' });
                                                }
                                            }}
                                            className="hidden md:flex p-1 ml-1 rounded-full bg-slate-800/80 backdrop-blur-sm text-slate-300 hover:bg-slate-700 pointer-events-auto border border-slate-700/50 shadow-sm transition-all"
                                        >
                                            <ChevronLeft className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                )}

                                {/* Desktop Scroll Button Right */}
                                {showRightFade && (
                                    <div className="absolute right-0 top-0 bottom-0 flex items-center justify-end bg-gradient-to-l from-surface via-surface to-transparent pl-4 z-10 pointer-events-none">
                                        <button 
                                            onClick={(e) => {
                                                e.preventDefault();
                                                if (genreScrollRef.current) {
                                                    genreScrollRef.current.scrollBy({ left: 200, behavior: 'smooth' });
                                                }
                                            }}
                                            className="hidden md:flex p-1 mr-1 rounded-full bg-slate-800/80 backdrop-blur-sm text-slate-300 hover:bg-slate-700 pointer-events-auto border border-slate-700/50 shadow-sm transition-all"
                                        >
                                            <ChevronRight className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                )}

                                <div 
                                    ref={genreScrollRef}
                                    className="flex gap-1.5 overflow-x-auto no-scrollbar items-center scroll-smooth pr-10 w-full"
                                >
                                    <button
                                        onClick={() => handleGenreSelect(null)}
                                        className={`px-3 py-1.5 rounded-full text-[12px] font-bold uppercase tracking-wider transition-all shrink-0 border ${
                                            archiveGenre.length === 0
                                                ? 'bg-primary/20 border-primary/40 text-primary' 
                                                : 'bg-slate-900/50 border-slate-800 text-slate-500 hover:border-slate-700'
                                        }`}
                                    >
                                        Alle
                                    </button>
                                    {GENRES.filter(g => availableGenres.includes(g.value)).map(g => (
                                        <button
                                            key={g.value}
                                            onClick={() => handleGenreSelect(g.value)}
                                            className={`px-3 py-1.5 rounded-full text-[12px] font-bold uppercase tracking-wider transition-all shrink-0 border ${
                                                archiveGenre.includes(g.value)
                                                    ? 'bg-primary/20 border-primary/40 text-primary' 
                                                    : 'bg-slate-900/50 border-slate-800 text-slate-500 hover:border-slate-700'
                                            }`}
                                        >
                                            {g.label}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {stories.length === 0 ? (
                <div className="text-center py-20 animate-in fade-in duration-700">
                    <div className="w-24 h-24 mx-auto bg-surface rounded-[2rem] flex items-center justify-center mb-6 shadow-sm border border-slate-800">
                        <BookOpen className="w-10 h-10 text-slate-700" />
                    </div>
                    <h2 className="text-2xl text-text mb-2 font-semibold">
                        {archiveFilter === 'public' && 'Noch keine öffentlichen Geschichten'}
                        {archiveFilter === 'favorites' && 'Deine Sammlung ist leer'}
                        {archiveFilter === 'my' && 'Deine Entwürfe sind leer'}
                    </h2>
                    <p className="text-slate-500 text-sm max-w-[280px] mx-auto leading-relaxed">
                        {archiveFilter === 'public' && 'Erstelle die erste öffentliche Geschichte im Labor!'}
                        {archiveFilter === 'favorites' && 'Markiere Geschichten mit einem Herz, um sie deiner Sammlung hinzuzufügen.'}
                        {archiveFilter === 'my' && 'Hier werden deine Entwürfe sicher aufbewahrt. Erstelle deine erste Geschichte im Labor!'}
                    </p>
                    <button 
                        onClick={() => setActiveView(archiveFilter === 'favorites' ? 'discover' : 'create')}
                        className="btn-primary mt-8 px-8 mx-auto block"
                    >
                        {archiveFilter === 'favorites' ? 'Entdecken' : 'Jetzt starten'}
                    </button>
                </div>
            ) : archiveFilter === 'public' && !archiveSearch && archiveGenre.length === 0 ? (
                <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
                    <HeroSection 
                        story={stories[0]} 
                        onPlay={handlePlay} 
                        onFavorite={toggleFavorite} 
                    />
                    
                    <CollectionRow 
                        title="Neu bei storyja" 
                        stories={stories.slice(1, 11)} 
                        onPlay={handlePlay} 
                        onFavorite={toggleFavorite}
                        onToolbox={setShowToolbox}
                    />
                    
                    <CollectionRow 
                        title="Zauberhafte Märchen" 
                        stories={fairytales} 
                        onPlay={handlePlay} 
                        onFavorite={toggleFavorite}
                        onToolbox={setShowToolbox}
                    />

                    <CollectionRow 
                        title="Action & Abenteuer" 
                        stories={adventure} 
                        onPlay={handlePlay} 
                        onFavorite={toggleFavorite}
                        onToolbox={setShowToolbox}
                    />

                    <CollectionRow 
                        title="Schlaf gut" 
                        stories={sleepStories} 
                        onPlay={handlePlay} 
                        onFavorite={toggleFavorite}
                        onToolbox={setShowToolbox}
                    />

                    <CollectionRow 
                        title="Zukunft & Weltraum" 
                        stories={scifi} 
                        onPlay={handlePlay} 
                        onFavorite={toggleFavorite}
                        onToolbox={setShowToolbox}
                    />
                </div>
            ) : archiveFilter === 'public' && !archiveSearch && archiveGenre.length > 0 ? (
                <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
                    <HeroSection 
                        story={stories[0]} 
                        onPlay={handlePlay} 
                        onFavorite={toggleFavorite} 
                    />
                    <h3 className="text-xs font-bold uppercase tracking-[0.25em] text-slate-500 mb-6 ml-1 flex items-center gap-2.5">
                        <BookOpen className="w-4 h-4 text-primary" />
                        {archiveGenre.length === 1 ? archiveGenre[0] : 'Entdeckungen'}
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-x-4 gap-y-8 mb-12">
                        {stories.slice(1).map(story => (
                            <FlipStoryCard 
                                key={story.id} 
                                story={story} 
                                onPlay={handlePlay} 
                                onFavorite={toggleFavorite} 
                                onToolbox={setShowToolbox}
                            />
                        ))}
                    </div>
                </div>
            ) : archiveFilter === 'favorites' ? (
                <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-x-4 gap-y-8 mb-12">
                        {stories.map(story => (
                            <FlipStoryCard 
                                key={story.id} 
                                story={story} 
                                onPlay={handlePlay} 
                                onFavorite={toggleFavorite} 
                                onToolbox={setShowToolbox}
                            />
                        ))}
                    </div>
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {stories.map(story => (
                        <div
                            key={story.id}
                            className={`bg-surface border border-slate-800 rounded-3xl p-5 hover:shadow-xl hover:shadow-primary/5 transition-all duration-300 group mb-4 relative overflow-hidden ${story.status === 'generating' ? 'ring-1 ring-primary/20' : ''}`}
                        >
                            <div className="flex items-start gap-4">
                                {story.image_url ? (
                                    <div
                                        className="w-20 h-20 rounded-2xl overflow-hidden shrink-0 shadow-sm border border-slate-700 cursor-pointer"
                                        onClick={() => handlePlay(story.id)}
                                    >
                                        <img src={getThumbUrl(story.id, story.updated_at)} alt={story.title} className="w-full h-full object-cover grayscale-[20%] scale-110" />
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
                                                <div className="text-lg font-semibold text-primary/40 animate-pulse flex flex-wrap gap-x-1">
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
                                                <h3 className="text-xl font-semibold text-text group-hover:text-primary transition-colors leading-tight cursor-pointer" onClick={() => story.status === 'done' && handlePlay(story.id)}>
                                                    {story.title}
                                                </h3>
                                            )}
                                        </div>
                                        
                                        <div className="flex gap-6 mb-1">
                                            <div className="flex flex-col">
                                                <span className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-0.5">Genre</span>
                                                <span className="text-sm text-slate-300 font-bold">{story.genre || '—'}</span>
                                            </div>
                                            <div className="flex flex-col flex-1 min-w-0">
                                                <span className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-0.5">Stil</span>
                                                <span className="text-sm text-slate-300 font-medium">
                                                    {story.style.split(',').map(id => authorName(id.trim())).join(', ')}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="mt-3">
                                {/* The Idea / Prompt (Only in Library) */}
                                {archiveFilter === 'my' && (
                                    <div className="bg-background/40 border border-slate-800/50 rounded-xl p-3 text-xs text-slate-500 italic mb-3">
                                        <span className="font-bold uppercase tracking-wider text-xs block mb-1 text-slate-600 not-italic">Die Idee</span>
                                        {story.prompt}
                                    </div>
                                )}

                                {/* Progress/Status during generation/error */}
                                {story.status === 'generating' && (
                                    <div className="mb-4 space-y-2 w-full">
                                        <div className="flex justify-between items-end">
                                            <div className="flex items-center gap-2 text-primary text-xs font-semibold">
                                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                {story.progress || 'Planung...'}
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <button 
                                                    onClick={(e) => { e.stopPropagation(); if(confirm('Möchtest du diese Generierung wirklich abbrechen?')) deleteStory(story.id); }}
                                                    className="text-[10px] uppercase font-bold tracking-wider text-red-500/60 hover:text-red-500 transition-colors"
                                                >
                                                    Abbrechen
                                                </button>
                                                <span className="text-xs font-bold text-primary bg-accent/20 px-1.5 py-0.5 rounded-md">
                                                    {story.progress_pct || 0}%
                                                </span>
                                            </div>
                                        </div>
                                        <div className="w-full h-1.5 bg-accent/20 rounded-full overflow-hidden border border-primary/20">
                                            <div
                                                className="h-full bg-primary transition-all duration-1000 ease-out"
                                                style={{ width: `${story.progress_pct || 0}%` }}
                                            />
                                        </div>
                                    </div>
                                )}
                                
                                {story.status === 'error' && (
                                    <div className="mb-4">
                                        <div className="px-3 py-2 bg-red-950/20 text-red-500 rounded-lg text-xs font-medium w-full border border-red-900/30 italic line-clamp-2 hover:line-clamp-none transition-all cursor-help" title={story.progress || 'Fehler bei der Erstellung'}>
                                            {story.progress || 'Fehler bei der Erstellung'}
                                        </div>
                                    </div>
                                )}

                                {/* Full Synopsis - Show if available and NOT the initial 100-char prompt copy (which usually happens during very early generation) */}
                                {story.description && (story.status === 'done' || (story.status === 'generating' && story.description.length > 100)) && (
                                    <div className="relative">
                                        <p className={`text-sm text-text/90 leading-relaxed italic ${expandedStories.has(story.id) ? '' : 'line-clamp-3'}`}>
                                            {story.description}{!expandedStories.has(story.id) && story.description.length > 150 ? '...' : ''}
                                        </p>
                                        {!expandedStories.has(story.id) && story.description.length > 150 && (
                                            <div className="absolute bottom-0 right-0 h-5 pl-16 bg-gradient-to-l from-surface via-surface/90 to-transparent flex items-center">
                                                <button 
                                                    onClick={(e) => { e.stopPropagation(); toggleExpand(story.id); }}
                                                    className="text-xs font-bold text-primary hover:text-emerald-400 uppercase tracking-wider transition-colors"
                                                >
                                                    Mehr lesen
                                                </button>
                                            </div>
                                        )}
                                        {expandedStories.has(story.id) && (
                                            <button 
                                                onClick={(e) => { e.stopPropagation(); toggleExpand(story.id); }}
                                                className="text-xs font-bold text-primary hover:text-emerald-400 mt-1 uppercase tracking-wider transition-colors block"
                                            >
                                                Weniger anzeigen
                                            </button>
                                        )}
                                    </div>
                                )}
                            </div>

                            {(story.status === 'done' || story.status === 'error') && (
                                <div className="mt-4">
                                    <div className="h-px bg-slate-800/50 w-full mb-3" />
                                    
                                    <div className="flex items-end justify-between px-2">
                                        {/* Left: Metadata */}
                                        <div className="flex flex-col gap-1 text-xs text-slate-500 font-medium">
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
                                            {archiveFilter === 'my' && story.is_public && (
                                                <div className="mt-1">
                                                    <span className="px-1.5 py-0.5 rounded-md bg-slate-800 border border-slate-700 text-xs font-bold text-slate-400 uppercase tracking-wider animate-in fade-in slide-in-from-left-1 duration-500">
                                                        Veröffentlicht
                                                    </span>
                                                </div>
                                            )}
                                        </div>

                                        {/* Center/Right Actions */}
                                        <div className="flex items-center gap-2">
                                            {/* Listen Button */}
                                            <button
                                                onClick={() => handlePlay(story.id)}
                                                className="w-11 h-11 bg-accent/20 border border-emerald-500/30 rounded-xl flex items-center justify-center text-primary hover:bg-accent/30 hover:border-emerald-500/50 transition-all active:scale-90 shadow-lg shadow-primary/10"
                                                title="Anhören"
                                            >
                                                <Play className="w-5 h-5 fill-current" />
                                            </button>

                                            {/* Favorite Button */}
                                            <button
                                                onClick={(e) => { 
                                                    e.stopPropagation(); 
                                                    if (!user) {
                                                        toast.error('Bitte melde dich an, um die Sammlung zu nutzen');
                                                        return;
                                                    }
                                                    toggleFavorite(story.id); 
                                                }}
                                                className={`w-11 h-11 rounded-xl flex items-center justify-center border transition-all active:scale-90 ${
                                                    story.is_favorite 
                                                    ? 'bg-red-500/10 border-red-500/50 text-red-500 shadow-lg shadow-red-500/10' 
                                                    : 'bg-slate-900/80 border-slate-700/50 text-slate-400 hover:text-red-400 hover:border-red-400/30'
                                                }`}
                                                title={story.is_favorite ? "Aus Sammlung entfernen" : "Zur Sammlung hinzufügen"}
                                            >
                                                <Heart className={`w-5 h-5 ${story.is_favorite ? 'fill-current' : ''}`} />
                                            </button>

                                            {/* Toolbox Button */}
                                            <button
                                                onClick={() => setShowToolbox(story.id)}
                                                className="w-11 h-11 bg-slate-900/80 border border-slate-700/50 rounded-xl flex items-center justify-center text-slate-400 hover:text-primary hover:border-primary/50 transition-all active:scale-90"
                                                title="Werkzeuge"
                                            >
                                                <Wand2 className="w-5 h-5" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Sentinel for Infinite Scroll */}
            <div ref={observerTarget} className="h-20 flex items-center justify-center">
                {isLoading && stories.length > 0 && (
                    <div className="flex flex-col items-center gap-2 animate-in fade-in duration-300">
                        <Loader2 className="w-6 h-6 text-primary animate-spin" />
                        <span className="text-xs uppercase tracking-widest text-slate-500 font-bold">Lade mehr...</span>
                    </div>
                )}
                {!hasMore && stories.length > 0 && archiveFilter !== 'my' && (
                    <div className="text-xs uppercase tracking-widest text-slate-700 font-bold">
                        Dich erwarten bald neue Geschichten
                    </div>
                )}
            </div>

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
                                                        <div className={`text-xs ${selectedVoice === v.key ? 'text-primary' : 'text-slate-600'}`}>
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
                                    <label className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-1.5 ml-1">
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

                                <p className="text-xs text-slate-500 text-center leading-relaxed">
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
                            <h2 className="text-sm uppercase tracking-widest text-slate-300 font-bold">
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
                                        {archiveFilter === 'my' && activeToolboxStory.user_id === user?.id && (
                                            <div className={`${itemClass} flex-col !items-start gap-1.5`}>
                                                <div className="flex items-center gap-2">
                                                    <Sparkles className="w-3.5 h-3.5 text-primary shrink-0" />
                                                    <span className={itemLabelClass}>Veröffentlichen</span>
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
                                        {archiveFilter === 'my' && (activeToolboxStory.user_id === user?.id || user?.is_admin) && (
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
                                            <div className={`${itemClass} flex-col !items-start gap-1.5`}>
                                                <div className="flex items-center gap-2">
                                                    <Play className="w-3.5 h-3.5 text-[#1DB954] shrink-0" />
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
                                                className={`${itemClass} border-red-500/20 hover:bg-red-500/10 hover:border-red-500/40 group/delete col-span-2`}
                                            >
                                                <Trash2 className="w-4 h-4 text-red-500 shrink-0 opacity-70 group-hover/delete:opacity-100" />
                                                <span className={`${itemLabelClass} group-hover/delete:text-red-500`}>Löschen</span>
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

            <ConfirmModal 
                isOpen={!!deleteConfirm}
                title="Geschichte löschen"
                message={`Möchtest du "${deleteConfirm?.title}" wirklich unwiderruflich löschen?`}
                onConfirm={confirmDelete}
                onClose={() => setDeleteConfirm(null)}
            />
        </div>
    );
}

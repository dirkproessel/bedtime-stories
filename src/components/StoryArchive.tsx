import { useStore } from '../store/useStore';
import { getVoicePreviewUrl, exportStoryToKindle, getThumbUrl, getImageUrl, regenerateStoryImage } from '../lib/api';
import { Play, Trash2, Heart, BookOpen, Loader2, Mic, X, XCircle, Venus, Mars, Users, Pause, Send, Image as ImageIcon, RefreshCw, Sparkles, Settings2, MessageCircle, Search, ChevronLeft, ChevronRight, ArrowLeft, Wand2, User as UserIcon, Clock } from 'lucide-react';
import toast from 'react-hot-toast';
import { useEffect, useState, useRef } from 'react';
import ConfirmModal from './ConfirmModal';


import { voiceName, voiceDesc } from '../lib/voices';
import { GENRES } from './StoryCreator';
import { formatAuthorStyles } from '../lib/authors';

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


function ManagementStoryCard({ 
    story, 
    onPlay, 
    onFavorite, 
    onToolbox,
    onDelete,
    formatDuration
}: { 
    story: any, 
    onPlay: (id: string) => void, 
    onFavorite: (id: string) => void, 
    onToolbox: (id: string) => void,
    onDelete: (id: string, title: string) => void,
    formatDuration: (seconds: number) => string
}) {
    if (!story) return null;

    return (
        <div className="bg-[#12181f] border border-slate-800/80 rounded-3xl p-5 mb-5 shadow-lg shadow-black/20 hover:border-slate-700/50 transition-all duration-300 group relative overflow-hidden">
            {/* Header: Image left, Title+Meta right */}
            <div className="flex gap-4 mb-4">
                {/* Image Section */}
                <div 
                    className="w-24 h-24 sm:w-28 sm:h-28 rounded-2xl overflow-hidden shrink-0 cursor-pointer border border-slate-700/50 shadow-sm relative bg-slate-900 flex items-center justify-center"
                    onClick={() => story.status === 'done' && onPlay(story.id)}
                >
                    {story.status === 'generating' && !story.image_url ? (
                        <div className="w-full h-full inset-0 absolute generating-placeholder flex items-center justify-center">
                            <Loader2 className="w-8 h-8 text-primary animate-spin opacity-40" />
                        </div>
                    ) : (
                        <img 
                            src={getThumbUrl(story.id, story.status === 'generating' ? `${story.updated_at}_${Date.now()}` : story.updated_at)} 
                            alt={story.title}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" 
                        />
                    )}
                </div>
                
                {/* Information Section */}
                <div className="flex-1 min-w-0 flex flex-col pt-1">
                    <h3 
                        className={`text-lg sm:text-xl font-bold leading-tight mb-3 cursor-pointer hover:text-primary transition-colors pr-2 font-serif ${
                            story.status === 'generating' && story.title.includes('Schreibe Dein') ? 'matrix-text' : 'text-white'
                        }`}
                        onClick={() => story.status === 'done' && onPlay(story.id)}
                    >
                        {story.status === 'generating' && story.title.includes('Schreibe Dein') 
                            ? "Lorem ipsum dolor sit amet" 
                            : story.title}
                    </h3>
                    
                    <div className="flex gap-6">
                        <div className="flex flex-col">
                            <span className="text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-1.5">Genre</span>
                            <span className="text-[13px] font-bold text-slate-200">
                                {story.genre}
                            </span>
                        </div>
                        <div className="flex flex-col min-w-0 pr-2">
                            <span className="text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-1.5">Stil</span>
                            <span className="text-[13px] font-medium text-slate-200 leading-snug">
                                {formatAuthorStyles(story.style)}
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Synopsis */}
            <p className="text-[14px] text-slate-300 italic leading-[1.6] font-normal mb-5 pr-2">
                {story.description}
            </p>

            {/* Footer */}
            <div className="flex justify-between items-end border-t border-slate-800/50 pt-4 mt-auto">
                {/* Left Stats & Status */}
                <div className="flex flex-col gap-1.5">
                    <div className="flex flex-col items-start gap-1.5">
                        {story.word_count > 0 && (
                            <div className="flex items-center gap-2 text-[12px] font-semibold text-slate-500">
                                <BookOpen className="w-4 h-4 text-slate-600" />
                                {story.word_count} Worte
                            </div>
                        )}
                        {story.voice_key !== 'none' && (
                            <div className="flex items-center gap-2 text-[12px] font-semibold text-slate-500">
                                <Clock className="w-4 h-4 text-slate-600" />
                                {formatDuration(story.duration_seconds)} Min ({voiceName(story.voice_key)})
                            </div>
                        )}
                    </div>
                    <div className="mt-1">
                        {story.is_public ? (
                            <div className="inline-flex px-3 py-1.5 bg-[#1b253b] border border-[#2d3b5b] text-[#869abf] text-[10px] font-bold uppercase tracking-wider rounded-md w-max">
                                 VERÖFFENTLICHT
                            </div>
                        ) : (
                            <div className="inline-flex px-3 py-1.5 bg-slate-800/50 border border-slate-700/50 text-slate-400 text-[10px] font-bold uppercase tracking-wider rounded-md w-max">
                                PRIVAT
                            </div>
                        )}
                    </div>
                </div>

                {/* Right Buttons */}
                <div className="flex items-center gap-2">
                    <button
                        onClick={(e) => { e.stopPropagation(); onPlay(story.id); }}
                        className="w-10 h-10 bg-[#082a17] border border-[#134226] rounded-[0.8rem] flex items-center justify-center transition-all hover:bg-[#0c3a21]"
                    >
                        <Play className="w-4 h-4 text-[#1DB954] fill-current ml-0.5" />
                    </button>
                    <button
                        onClick={(e) => { e.stopPropagation(); onFavorite(story.id); }}
                        className={`w-10 h-10 rounded-[0.8rem] flex items-center justify-center border transition-all ${
                            story.is_favorite 
                            ? 'bg-[#3b1216] border-[#5e1e24] text-[#ff4b55]' 
                            : 'bg-[#3b1216] border-[#5e1e24] text-[#ff4b55] opacity-50 hover:opacity-100' // If not favorited, just dim it slightly based on screenshot? Wait, standard heart toggle...
                        }`}
                        title={story.is_favorite ? 'Von Favoriten entfernen' : 'Zu Favoriten hinzufügen'}
                    >
                        {/* Assuming the screenshot has it filled if it's red */}
                        <Heart className="w-4 h-4 text-[#ff4b55] fill-current" />
                    </button>
                    <button
                        onClick={(e) => { e.stopPropagation(); onToolbox(story.id); }}
                        className="w-10 h-10 bg-[#151a28] border border-[#212a40] rounded-[0.8rem] flex items-center justify-center transition-all hover:bg-[#1f273b]"
                    >
                        <Wand2 className="w-4 h-4 text-[#7584a5]" />
                    </button>
                </div>
            </div>

            {story.status === 'generating' && (
                <div className="mt-4 pt-4 border-t border-slate-800/50 animate-in fade-in slide-in-from-bottom-2 duration-700">
                    <div className="flex justify-between items-end mb-2.5">
                        <div className="flex flex-col">
                            <span className="text-[10px] uppercase font-bold text-slate-500 tracking-[0.2em] mb-0.5">Fortschritt</span>
                            <span className="text-[13px] font-bold text-primary flex items-center gap-2">
                                {story.progress || 'Generierung wird vorbereitet...'}
                            </span>
                        </div>
                        <div className="flex items-center gap-4">
                            <button 
                                onClick={(e) => { e.stopPropagation(); onDelete(story.id, story.title); }}
                                className="text-[10px] font-extrabold text-red-500 hover:text-red-400 uppercase tracking-widest transition-all flex items-center gap-1.5 px-2 py-1 bg-red-500/10 rounded-md border border-red-500/20"
                                title="Generierung abbrechen"
                            >
                                <XCircle className="w-3.5 h-3.5" />
                                Abbrechen
                            </button>
                            <span className="text-[15px] font-medium text-primary/90 font-sans tracking-tight min-w-[36px] text-right">
                                {story.progress_pct || 0}%
                            </span>
                        </div>
                    </div>

                    {/* Continuous Progress Bar */}
                    <div className="h-1.5 w-full bg-slate-800/50 rounded-full overflow-hidden border border-white/5">
                        <div 
                            className="h-full bg-primary shadow-[0_0_10px_rgba(34,197,94,0.3)] transition-all duration-700 ease-out rounded-full"
                            style={{ width: `${story.progress_pct || 0}%` }}
                        />
                    </div>
                </div>
            )}
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
        <div className="py-4 w-full mx-auto">

            {/* Mobile Filter Bar (Hidden on Desktop as we use sidebar there now) */}
            <div className={`lg:hidden mb-4 sticky top-0 z-30 bg-background/80 backdrop-blur-md pb-2 -mx-3 px-3 sm:-mx-6 sm:px-6 transition-all duration-300 ${isScrolled ? 'border-b border-primary/20 shadow-sm' : 'border-transparent'}`}>
                <div className="relative flex items-center h-10 bg-surface/50 border border-slate-800 rounded-2xl overflow-hidden transition-all duration-300">
                    
                    {filterLevel === 'main' && (
                        <div className="flex-1 flex w-full items-center px-2 gap-2 animate-in fade-in zoom-in-95 duration-200">
                            <button 
                                onClick={() => setFilterLevel('search')}
                                className={`flex items-center gap-2 px-3 h-7 rounded-xl text-sm font-medium transition-colors ${
                                    archiveSearch ? 'bg-primary/20 text-primary border border-primary/20' : 'bg-slate-800/50 hover:bg-slate-800 text-slate-300 border border-transparent'
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
            ) : (
                <>
                    <div className="flex flex-col lg:flex-row gap-8 items-start">
                        <div className="flex-1 w-full min-w-0">
                            {/* Main Content Areas */}
                            {archiveFilter === 'public' && !archiveSearch && archiveGenre.length === 0 ? (
                                <div className="space-y-12 animate-in fade-in duration-700">
                                    <HeroSection 
                                        story={stories[0]} 
                                        onPlay={handlePlay} 
                                        onFavorite={toggleFavorite} 
                                    />
                                    <div className="space-y-16">
                                        <CollectionRow title="Magische Märchen" stories={fairytales} onPlay={handlePlay} onFavorite={toggleFavorite} onToolbox={setShowToolbox} />
                                        <CollectionRow title="Große Abenteuer" stories={adventure} onPlay={handlePlay} onFavorite={toggleFavorite} onToolbox={setShowToolbox} />
                                        <CollectionRow title="Zum Einschlafen" stories={sleepStories} onPlay={handlePlay} onFavorite={toggleFavorite} onToolbox={setShowToolbox} />
                                        <CollectionRow title="Science-Fiction" stories={scifi} onPlay={handlePlay} onFavorite={toggleFavorite} onToolbox={setShowToolbox} />
                                    </div>
                                </div>
                            ) : (archiveFilter === 'public' && (archiveSearch || archiveGenre.length > 0)) || archiveFilter === 'favorites' ? (
                                <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
                                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-8 mb-12">
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
                                <div className="grid grid-cols-1 gap-6">
                                    {stories.map(story => (
                                        <ManagementStoryCard 
                                            key={story.id} 
                                            story={story} 
                                            onPlay={handlePlay}
                                            onFavorite={toggleFavorite}
                                            onToolbox={setShowToolbox}
                                            onDelete={handleDelete}
                                            formatDuration={formatDuration}
                                        />
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Desktop Sidebar Filters (Restored) */}
                        <aside className="hidden lg:block w-72 shrink-0 h-fit sticky top-24 animate-in fade-in duration-700">
                            <div className="bg-surface/50 border border-slate-800 rounded-[2rem] p-6 shadow-xl shadow-black/20">
                                <div className="mb-8">
                                    <div className="flex items-center gap-2 mb-4 px-2">
                                        <Search className="w-4 h-4 text-primary" />
                                        <span className="text-xs uppercase tracking-[0.2em] text-slate-500 font-bold">Suchen</span>
                                    </div>
                                    <div className="relative group">
                                        <input 
                                            type="text"
                                            value={searchValue}
                                            onChange={(e) => setSearchValue(e.target.value)}
                                            placeholder="Titel oder Thema..."
                                            className="w-full pl-10 pr-4 py-3 bg-slate-900 border-2 border-slate-800 rounded-2xl text-sm focus:outline-none focus:border-primary transition-all placeholder:text-slate-700 font-medium"
                                        />
                                        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-700 group-focus-within:text-primary transition-colors" />
                                    </div>
                                </div>

                                <div>
                                    <div className="flex items-center gap-2 mb-4 px-2">
                                        <BookOpen className="w-4 h-4 text-primary" />
                                        <span className="text-xs uppercase tracking-[0.2em] text-slate-500 font-bold">Genre Filter</span>
                                    </div>
                                    <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2 no-scrollbar">
                                        <button
                                            onClick={() => handleGenreSelect(null)}
                                            className={`w-full flex items-center justify-between px-4 py-2.5 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-all border-2 ${
                                                archiveGenre.length === 0
                                                    ? 'bg-primary/10 border-primary text-primary' 
                                                    : 'bg-slate-900 border-slate-800/50 text-slate-500 hover:border-slate-700'
                                            }`}
                                        >
                                            <span>Alle</span>
                                        </button>
                                        {GENRES.filter(g => availableGenres.includes(g.value)).map(g => (
                                            <button
                                                key={g.value}
                                                onClick={() => handleGenreSelect(g.value)}
                                                className={`w-full flex items-center justify-between px-4 py-2.5 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-all border-2 ${
                                                    archiveGenre.includes(g.value)
                                                        ? 'bg-primary/10 border-primary text-primary' 
                                                        : 'bg-slate-900 border-slate-800/50 text-slate-500 hover:border-slate-700'
                                                }`}
                                            >
                                                <span className="truncate">{g.label}</span>
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="pt-8 mt-8 border-t border-slate-800/50">
                                    <div className="flex items-center justify-between text-[10px] uppercase font-bold tracking-[0.2em] text-slate-600">
                                        <span>Gesamt</span>
                                        <span>
                                            {archiveFilter === 'my' ? totalMyStories : 
                                             archiveFilter === 'public' ? totalPublicStories : 
                                             totalStories}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </aside>
                    </div>

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
                </>
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
                <div className="fixed inset-0 z-[100] flex items-end lg:items-center justify-center lg:justify-end bg-background/70 backdrop-blur-sm animate-in fade-in duration-500">
                    <div 
                        className="fixed inset-0" 
                        onClick={() => setShowToolbox(null)}
                    />
                    <div className="relative w-full max-w-[320px] h-full bg-[#12181f] border-t lg:border-t-0 lg:border-l border-slate-800/80 p-5 shadow-2xl animate-in slide-in-from-bottom lg:slide-in-from-right duration-300">
                        <div className="flex flex-col mb-4 pr-6">
                            <h2 className="text-[14px] uppercase tracking-[0.2em] text-[#e2e8f0] font-bold">
                                WERKZEUGKASTEN
                            </h2>
                            {activeToolboxStory && (
                                <p className="text-[#64748b] text-[12px] mt-1 truncate">
                                    "{activeToolboxStory.title}"
                                </p>
                            )}
                        </div>
                        <button
                            onClick={() => setShowToolbox(null)}
                            className="absolute top-5 right-5 text-slate-500 hover:text-white transition-all"
                        >
                            <X className="w-5 h-5" />
                        </button>

                        {activeToolboxStory && (
                            <div className="flex flex-col gap-0.5">
                                {/* Remix Labor */}
                                <div className="text-[10px] uppercase text-[#64748b] font-bold tracking-widest mt-2 mb-1 px-2">REMIX LABOR</div>
                                
                                <button 
                                    onClick={() => { setShowRemixModal(activeToolboxStory.id); setRemixType('sequel'); setShowToolbox(null); }}
                                    className="w-full flex items-center gap-3 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-all outline-none"
                                >
                                    <div className="w-8 h-8 rounded-[0.4rem] flex items-center justify-center shrink-0 bg-[#082a17] text-[#1DB954]">
                                        <Play className="w-4 h-4 fill-current ml-0.5" />
                                    </div>
                                    <div className="text-left text-[14px] text-[#e2e8f0]">
                                        Fortsetzung schreiben
                                    </div>
                                </button>

                                <button 
                                    onClick={() => { setShowRemixModal(activeToolboxStory.id); setRemixType('improvement'); setShowToolbox(null); }}
                                    className="w-full flex items-center gap-3 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-all outline-none"
                                >
                                    <div className="w-8 h-8 rounded-[0.4rem] flex items-center justify-center shrink-0 bg-[#1e293b] text-[#818cf8]">
                                        <RefreshCw className="w-4 h-4" />
                                    </div>
                                    <div className="text-left text-[14px] text-[#e2e8f0]">
                                        Anpassen / Verbessern
                                    </div>
                                </button>

                                {/* Werkzeuge */}
                                <div className="text-[10px] uppercase text-[#64748b] font-bold tracking-widest mt-3 mb-1 px-2">WERKZEUGE</div>
                                
                                <button 
                                    onClick={() => { setRevoiceStoryId(activeToolboxStory.id); setConfirmRevoice(false); setShowToolbox(null); }}
                                    className="w-full flex items-center gap-3 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-all outline-none"
                                >
                                    <div className="w-8 h-8 bg-[#064e3b] rounded-[0.4rem] flex items-center justify-center shrink-0 text-[#34d399]">
                                        <Mic className="w-4 h-4" />
                                    </div>
                                    <div className="text-left text-[14px] text-[#e2e8f0]">
                                        Neu vertonen
                                    </div>
                                </button>

                                <button 
                                    onClick={() => { handleRegenerateImage(activeToolboxStory.id); setShowToolbox(null); }}
                                    className="w-full flex items-center gap-3 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-all outline-none"
                                >
                                    <div className="w-8 h-8 bg-[#7c2d12] rounded-[0.4rem] flex items-center justify-center shrink-0 text-[#fb923c]">
                                        <ImageIcon className="w-4 h-4" />
                                    </div>
                                    <div className="text-left text-[14px] text-[#e2e8f0]">
                                        Bild neu generieren
                                    </div>
                                </button>

                                {/* Sichtbarkeit & Versand */}
                                <div className="text-[10px] uppercase text-[#64748b] font-bold tracking-widest mt-3 mb-1 px-2">SICHTBARKEIT & VERSAND</div>
                                
                                {archiveFilter === 'my' && activeToolboxStory.user_id === user?.id && (
                                    <div className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-white/5 transition-all">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-[0.4rem] flex items-center justify-center shrink-0 bg-[#1e293b] text-[#64748b]">
                                                <Sparkles className="w-4 h-4" />
                                            </div>
                                            <div className="text-left text-[14px] text-[#e2e8f0]">
                                                Veröffentlichen
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
                                            className={`relative w-[34px] h-[20px] rounded-full transition-all duration-300 flex items-center p-0.5 shrink-0 ${
                                                activeToolboxStory.is_public ? 'bg-[#51618a]' : 'bg-[#1e293b]'
                                            }`}
                                        >
                                            <div className={`w-[16px] h-[16px] bg-white rounded-full transition-transform duration-300 transform ${
                                                activeToolboxStory.is_public ? 'translate-x-[14px]' : 'translate-x-0'
                                            } flex items-center justify-center`}>
                                                {isPublicLoading === activeToolboxStory.id && (
                                                    <Loader2 className="w-2.5 h-2.5 animate-spin text-primary" />
                                                )}
                                            </div>
                                        </button>
                                    </div>
                                )}

                                {user?.is_admin && (
                                    <div className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-white/5 transition-all">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-[0.4rem] flex items-center justify-center shrink-0 bg-[#1e293b] text-[#64748b]">
                                                <Play className="w-4 h-4 fill-current ml-0.5" />
                                            </div>
                                            <div className="text-left text-[14px] text-[#e2e8f0]">
                                                Spotify Podcast
                                            </div>
                                        </div>
                                        <button 
                                            onClick={() => {
                                                handleSpotifyToggle(activeToolboxStory.id, !activeToolboxStory.is_on_spotify);
                                            }}
                                            className={`relative w-[34px] h-[20px] rounded-full transition-all duration-300 flex items-center p-0.5 shrink-0 ${
                                                activeToolboxStory.is_on_spotify ? 'bg-[#51618a]' : 'bg-[#1e293b]'
                                            }`}
                                        >
                                            <div className={`w-[16px] h-[16px] bg-white rounded-full transition-transform duration-300 transform ${
                                                activeToolboxStory.is_on_spotify ? 'translate-x-[14px]' : 'translate-x-0'
                                            }`} />
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
                                    className="w-full flex items-center gap-3 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-all outline-none"
                                >
                                    <div className="w-8 h-8 bg-[#064e3b] rounded-[0.4rem] flex items-center justify-center shrink-0 text-[#1DB954]">
                                        <MessageCircle className="w-4 h-4" />
                                    </div>
                                    <div className="text-left text-[14px] text-[#e2e8f0]">
                                        Via WhatsApp teilen
                                    </div>
                                </button>

                                <button 
                                    onClick={() => { setShowKindleModal(activeToolboxStory.id); setShowToolbox(null); }}
                                    className="w-full flex items-center gap-3 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-all outline-none"
                                >
                                    <div className="w-8 h-8 bg-[#1e3a8a] rounded-[0.4rem] flex items-center justify-center shrink-0 text-[#60a5fa]">
                                        <Send className="w-4 h-4 ml-0.5 mt-0.5" />
                                    </div>
                                    <div className="text-left text-[14px] text-[#e2e8f0]">
                                        An Kindle senden
                                    </div>
                                </button>

                                {/* Löschen */}
                                {activeToolboxStory.user_id === user?.id && (
                                    <>
                                        <div className="mt-3"></div>
                                        <button 
                                            onClick={() => { handleDelete(activeToolboxStory.id, activeToolboxStory.title); setShowToolbox(null); }}
                                            className="w-full flex items-center gap-3 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-all outline-none group/delete"
                                        >
                                            <div className="w-8 h-8 bg-transparent rounded-[0.4rem] flex items-center justify-center shrink-0 text-[#64748b] group-hover/delete:bg-red-500/10 group-hover/delete:text-red-500 transition-colors">
                                                <Trash2 className="w-4 h-4" />
                                            </div>
                                            <div className="text-left text-[14px] text-[#64748b] group-hover/delete:text-red-400 transition-colors">
                                                Geschichte löschen
                                            </div>
                                        </button>
                                    </>
                                )}
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

import { useState, useEffect, useRef } from 'react';
import { useStore } from '../store/useStore';
import { 
    fetchStory, getThumbUrl, type StoryDetail, exportStoryToKindle, 
    getVoicePreviewUrl, regenerateStoryImage 
} from '../lib/api';
import { 
    Moon, BookOpen, Send, Loader2, MessageCircle, Headphones, Heart, 
    Wand2, ArrowLeft, User, Play, RefreshCw, Mic, 
    Image as ImageIcon, Sparkles, X, Pause
} from 'lucide-react';
import toast from 'react-hot-toast';
import { voiceName } from '../lib/voices';
import { formatAuthorStyles } from '../lib/authors';

export default function ReaderLayer() {
    const { 
        isReaderOpen, readerStoryId, setAudioCompanion, user,
        toggleFavorite, showAudioCompanion, setReaderOpen,
        revoiceStory, setGeneratorPrompt,
        setGeneratorGenre, setGeneratorAuthors, setGeneratorMinutes,
        setGeneratorVoice, setGeneratorRemix, setActiveView
    } = useStore();
    const [story, setStory] = useState<StoryDetail | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isExporting, setIsExporting] = useState(false);
    const [showKindleModal, setShowKindleModal] = useState(false);
    const [kindleEmail, setKindleEmail] = useState<string>(() => user?.kindle_email || localStorage.getItem('kindle_email') || '');
    const [showToolbox, setShowToolbox] = useState(false);
    const [isRegenerating, setIsRegenerating] = useState(false);
    const [showRevoiceModal, setShowRevoiceModal] = useState(false);
    const [selectedVoice, setSelectedVoice] = useState('seraphina');
    const [confirmRevoice, setConfirmRevoice] = useState(false);
    const [isRevoicing, setIsRevoicing] = useState(false);

    // Audio preview for re-voicing
    const [previewVoice, setPreviewVoice] = useState<string | null>(null);
    const audioRef = useRef<HTMLAudioElement>(null);
    const touchStartX = useRef<number | null>(null);
    const touchStartY = useRef<number | null>(null);

    const handleRegenerateImage = async () => {
        if (!readerStoryId) return;
        setIsRegenerating(true);
        try {
            await regenerateStoryImage(readerStoryId);
            toast.success('Bild-Regenerierung gestartet!');
        } catch (error: any) {
            toast.error(error.message || 'Fehler beim Starten');
        } finally {
            setIsRegenerating(false);
            setShowToolbox(false);
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

    const handleRevoice = async () => {
        if (!readerStoryId) return;
        setIsRevoicing(true);
        try {
            await revoiceStory(readerStoryId, selectedVoice);
            toast.success('Neuvertonung gestartet!');
            setShowRevoiceModal(false);
            setConfirmRevoice(false);
        } catch (error: any) {
            toast.error(error.message || 'Fehler beim Starten');
        } finally {
            setIsRevoicing(false);
        }
    };

    const handleTouchStart = (e: React.TouchEvent) => {
        touchStartX.current = e.touches[0].clientX;
        touchStartY.current = e.touches[0].clientY;
    };

    const handleTouchEnd = (e: React.TouchEvent) => {
        if (touchStartX.current === null || touchStartY.current === null) return;
        
        const touchEndX = e.changedTouches[0].clientX;
        const touchEndY = e.changedTouches[0].clientY;
        const deltaX = touchStartX.current - touchEndX;
        const deltaY = Math.abs(touchStartY.current - touchEndY);

        // Detect swipe from right to left (at least 70px) to OPEN
        // If it starts near the right edge (within 60px)
        const isFromRightEdge = touchStartX.current > window.innerWidth - 60;
        
        if (deltaX > 70 && deltaY < 50 && isFromRightEdge) {
            setShowToolbox(true);
        }

        // Detect swipe from left to right (at least 70px) to CLOSE
        // Only if toolbox is open
        if (showToolbox && deltaX < -70 && deltaY < 50) {
            setShowToolbox(false);
        }

        touchStartX.current = null;
        touchStartY.current = null;
    };

    useEffect(() => {
        if (isReaderOpen && readerStoryId) {
            setIsLoading(true);
            fetchStory(readerStoryId)
                .then(s => setStory(s))
                .catch(() => toast.error('Geschichte konnte nicht geladen werden'))
                .finally(() => setIsLoading(false));
        }
    }, [isReaderOpen, readerStoryId]);


    const handleKindleExport = async () => {
        if (!readerStoryId) return;
        if (!user) {
            toast.error('Bitte melde dich an');
            return;
        }
        setIsExporting(true);
        try {
            await exportStoryToKindle(readerStoryId, kindleEmail);
            toast.success('An Kindle gesendet!');
            setShowKindleModal(false);
        } catch (error: any) {
            toast.error(error.message || 'Fehler beim Export');
        } finally {
            setIsExporting(false);
        }
    };

    if (!isReaderOpen) return null;

    return (
        <div 
            className="fixed inset-0 z-[80] bg-background overflow-y-auto animate-in slide-in-from-bottom duration-300 ease-out flex flex-col items-center"
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
        >
            
            {/* Top Navigation Bar */}
            <header className="w-full h-16 flex items-center justify-between px-4 sm:px-8 bg-background/80 backdrop-blur-md border-b border-slate-800/50 sticky top-0 z-50 shrink-0">
                <button 
                    onClick={() => setReaderOpen(false)}
                    className="flex items-center gap-2 p-2 -ml-2 text-slate-400 hover:text-white transition-all group"
                >
                    <ArrowLeft className="w-6 h-6 group-hover:-translate-x-1 transition-transform" />
                    <span className="hidden sm:inline text-sm font-bold uppercase tracking-wider">Zurück</span>
                </button>

                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setShowToolbox(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-surface border border-slate-700 rounded-xl text-slate-300 hover:bg-slate-800 hover:text-white transition-all text-xs font-bold uppercase tracking-wider shadow-lg"
                    >
                        <Wand2 className="w-4 h-4 text-primary" />
                        <span className="hidden xs:inline">Werkzeuge</span>
                    </button>
                    <button 
                        onClick={() => setReaderOpen(false)}
                        className="p-2 text-slate-400 hover:text-white transition-all"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>
            </header>

            <div className="p-4 sm:p-6 w-full max-w-2xl lg:max-w-4xl pb-32">
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-20">
                        <div className="w-12 h-12 rounded-full border-4 border-[#F0FDF4] border-t-[#2D5A4C] animate-spin mb-4" />
                        <p className="text-slate-400 text-sm">Lade Geschichte…</p>
                    </div>
                ) : story ? (
                    <>
                        <div className="text-center mb-10">
                            {story.image_url ? (
                                <div className="w-56 h-56 mx-auto rounded-3xl overflow-hidden mb-6 shadow-2xl border-4 border-surface">
                                    <img src={getThumbUrl(story.id)} alt={story.title} className="w-full h-full object-cover" />
                                </div>
                            ) : (
                                <div className="w-32 h-32 mx-auto rounded-3xl bg-accent/20 flex items-center justify-center mb-6 shadow-xl shadow-primary/10">
                                    <Moon className="w-16 h-16 text-primary/90" />
                                </div>
                            )}

                            {/* Vorlesen Button - Centered under Image */}
                            {story.voice_key !== 'none' && (
                                <div className="flex justify-center mb-6">
                                    <button 
                                        onClick={() => setAudioCompanion(true, readerStoryId)}
                                        className="flex items-center gap-3 px-8 py-3 bg-primary text-white rounded-2xl text-sm font-bold shadow-xl shadow-primary/20 hover:bg-emerald-600 active:scale-95 transition-all"
                                    >
                                        <Headphones className="w-5 h-5" />
                                        Vorlesen
                                    </button>
                                </div>
                            )}
                            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-text font-serif leading-tight mb-4 px-4">{story.title}</h1>
                            
                            <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-3 mt-6 text-[11px] font-bold text-slate-500 uppercase tracking-[0.15em]">
                                {story.genre && (
                                    <span className="text-primary bg-primary/10 border border-primary/20 px-3 py-1 rounded-lg">
                                        {story.genre}
                                    </span>
                                )}
                                <span className="flex items-center gap-1.5 border-r border-slate-800 pr-6 last:border-0 last:pr-0">
                                    <BookOpen className="w-4 h-4 text-slate-600" />
                                    {story.word_count ? `${story.word_count} Worte` : 'Buch'}
                                </span>
                                {story.style && (
                                    <span className="flex items-center gap-1.5 border-r border-slate-800 pr-6 last:border-0 last:pr-0">
                                        <Sparkles className="w-4 h-4 text-slate-600" />
                                        {formatAuthorStyles(story.style)}
                                    </span>
                                )}
                                {story.voice_key !== 'none' && (
                                    <span className="flex items-center gap-1.5 border-r border-slate-800 pr-6 last:border-0 last:pr-0">
                                        <Mic className="w-4 h-4 text-slate-600" />
                                        {voiceName(story.voice_key)}
                                    </span>
                                )}
                                {story.user_email && user?.email !== story.user_email && (
                                    <span className="flex items-center gap-1.5 w-full justify-center mt-2 text-slate-600 lowercase tracking-normal font-medium italic">
                                        von {story.user_email}
                                    </span>
                                )}
                            </div>
                        </div>

                        <article className="prose prose-slate prose-invert max-w-none">
                            <div className="space-y-6">
                                {story.chapters && story.chapters.length > 0 ? (
                                    story.chapters.map((ch, idx) => (
                                        <div key={idx} className="space-y-4">
                                            <p className="story-text text-slate-300 font-serif whitespace-pre-line">
                                                {ch.text}
                                            </p>
                                        </div>
                                    ))
                                ) : (
                                    <p className="text-lg text-slate-400 leading-relaxed font-serif italic text-center py-10 opacity-60">
                                        Kein Textinhalt verfügbar.
                                    </p>
                                )}
                            </div>
                        </article>

                        <div className="mt-16 pt-8 border-t border-slate-800 flex flex-wrap items-center justify-center gap-4">
                            <button 
                                onClick={() => setShowKindleModal(true)}
                                className="flex items-center gap-2 px-5 py-2.5 bg-surface text-slate-300 rounded-2xl text-xs font-bold hover:bg-slate-800 transition-all border border-slate-700"
                            >
                                <Send className="w-4 h-4" />
                                Kindle
                            </button>
                            <button 
                                onClick={() => {
                                    const shareUrl = `${window.location.origin}${window.location.pathname}#/Story/${story.id}`;
                                    const text = `Schau mal: *${story.title}* 🌙✨\n\n${shareUrl}`;
                                    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
                                }}
                                className="flex items-center gap-2 px-5 py-2.5 bg-green-950/20 text-green-500 rounded-2xl text-xs font-bold hover:bg-green-950/30 transition-all border border-green-900/30"
                            >
                                <MessageCircle className="w-4 h-4" />
                                WhatsApp
                            </button>
                        </div>
                    </>
                ) : null}
            </div>

            {/* Kindle Modal (Simplified) */}
            {showKindleModal && (
                <div className="fixed inset-0 z-[120] flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
                    <div className="bg-surface rounded-[2.5rem] w-full max-w-sm p-8 shadow-2xl border border-slate-800 animate-in zoom-in duration-200">
                        <h2 className="text-2xl font-bold text-text mb-2">An Kindle senden</h2>
                        <p className="text-xs text-slate-500 mb-6 uppercase tracking-wider">E-Book Export</p>
                        <input 
                            type="email"
                            value={kindleEmail}
                            onChange={(e) => setKindleEmail(e.target.value)}
                            className="w-full px-5 py-4 bg-background border-2 border-slate-800 rounded-2xl mb-6 focus:border-primary transition-all outline-none text-text"
                            placeholder="deine.adresse@kindle.com"
                        />
                        <div className="flex gap-3">
                            <button onClick={() => setShowKindleModal(false)} className="flex-1 py-4 text-slate-500 font-bold hover:text-slate-300 transition-colors">Abbrechen</button>
                            <button 
                                onClick={handleKindleExport}
                                disabled={isExporting}
                                className="flex-[2] bg-primary text-white py-4 rounded-2xl font-bold shadow-lg shadow-primary/20 flex items-center justify-center gap-2 active:scale-95 transition-all"
                            >
                                {isExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                                Senden
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {/* Floating Action Button for Favorites */}
            <div 
                className={`fixed right-6 z-[110] transition-all duration-500 ease-in-out ${
                    showAudioCompanion ? 'bottom-[148px]' : 'bottom-[84px]'
                }`}
            >
                <button
                    onClick={() => {
                        if (!user) {
                            toast.error('Bitte melde dich an, um die Sammlung zu nutzen');
                            return;
                        }
                        story && toggleFavorite(story.id);
                    }}
                    className={`w-14 h-14 rounded-full flex items-center justify-center shadow-2xl backdrop-blur-md border transition-all active:scale-90 group ${
                        story?.is_favorite
                        ? 'bg-red-500/20 border-red-500/50 text-red-500'
                        : 'bg-slate-900/40 border-slate-700/50 text-slate-400 hover:text-red-400 hover:border-red-400/30'
                    }`}
                    aria-label={story?.is_favorite ? "Aus Sammlung entfernen" : "Zur Sammlung hinzufügen"}
                >
                    <Heart className={`w-7 h-7 transition-transform group-hover:scale-110 ${story?.is_favorite ? 'fill-current animate-pulse-subtle' : ''}`} />
                </button>
            </div>
            {/* Toolbox Overlay */}
            {showToolbox && story && (
                <div className="fixed inset-0 z-[120] flex items-stretch justify-end bg-background/70 animate-in fade-in duration-500">

                    <div 
                        className="fixed inset-0" 
                        onClick={() => setShowToolbox(false)}
                    />
                    <div className="relative w-full max-w-[320px] h-full bg-[#12181f] border-l border-slate-800/80 p-5 shadow-2xl animate-in slide-in-from-right duration-300">

                        <div className="flex flex-col mb-4 pr-6">
                            <h2 className="text-[14px] uppercase tracking-[0.2em] text-[#e2e8f0] font-bold">
                                WERKZEUGKASTEN
                            </h2>
                            <p className="text-[#64748b] text-[12px] mt-1 truncate">
                                "{story.title}"
                            </p>
                        </div>
                        <button
                            onClick={() => setShowToolbox(false)}
                            className="absolute top-5 right-5 text-slate-500 hover:text-white transition-all"
                        >
                            <X className="w-5 h-5" />
                        </button>

                        <div className="flex flex-col gap-0.5 mt-4">
                            {/* Remix Labor */}
                            <div className="text-[10px] uppercase text-[#64748b] font-bold tracking-widest mt-2 mb-1 px-2">REMIX LABOR</div>
                            
                            <button 
                                onClick={() => {
                                    setGeneratorGenre(story.genre);
                                    setGeneratorAuthors(story.style.split(',').map(s => s.trim()));
                                    setGeneratorMinutes(story.duration_seconds ? Math.ceil(story.duration_seconds / 60) : 15);
                                    setGeneratorVoice(story.voice_key);
                                    setGeneratorPrompt('');
                                    setGeneratorRemix(story.id, 'sequel', { title: story.title, synopsis: story.description });
                                    setReaderOpen(false);
                                    setActiveView('create');
                                    setShowToolbox(false);
                                }}
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
                                onClick={() => {
                                    setGeneratorGenre(story.genre);
                                    setGeneratorAuthors(story.style.split(',').map(s => s.trim()));
                                    setGeneratorMinutes(story.duration_seconds ? Math.ceil(story.duration_seconds / 60) : 15);
                                    setGeneratorVoice(story.voice_key);
                                    setGeneratorPrompt(story.prompt || '');
                                    setGeneratorRemix(story.id, 'improvement', null);
                                    setReaderOpen(false);
                                    setActiveView('create');
                                    setShowToolbox(false);
                                }}
                                className="w-full flex items-center gap-3 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-all outline-none"
                            >
                                <div className="w-8 h-8 rounded-[0.4rem] flex items-center justify-center shrink-0 bg-[#1e293b] text-[#818cf8]">
                                    <RefreshCw className="w-4 h-4" />
                                </div>
                                <div className="text-left text-[14px] text-[#e2e8f0]">
                                    Anpassen / Verbessern
                                </div>
                            </button>

                            {/* Werkzeuge - Owner Only */}
                            {user?.id === story.user_id && (
                                <>
                                    <div className="text-[10px] uppercase text-[#64748b] font-bold tracking-widest mt-4 mb-1 px-2">WERKZEUGE</div>
                                    
                                    <button 
                                        onClick={() => {
                                            setShowRevoiceModal(true);
                                            setShowToolbox(false);
                                        }}
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
                                        onClick={handleRegenerateImage}
                                        disabled={isRegenerating}
                                        className="w-full flex items-center gap-3 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-all outline-none"
                                    >
                                        <div className="w-8 h-8 bg-[#7c2d12] rounded-[0.4rem] flex items-center justify-center shrink-0 text-[#fb923c]">
                                            {isRegenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <ImageIcon className="w-4 h-4" />}
                                        </div>
                                        <div className="text-left text-[14px] text-[#e2e8f0]">
                                            Bild neu generieren
                                        </div>
                                    </button>
                                </>
                            )}


                            {/* Versand */}
                            <div className="text-[10px] uppercase text-[#64748b] font-bold tracking-widest mt-4 mb-1 px-2">VERSAND</div>
                            
                            <button 
                                onClick={() => {
                                    const shareUrl = `${window.location.origin}${window.location.pathname}#/Story/${story.id}`;
                                    const text = `Schau mal: *${story.title}* 🌙✨\n\n${shareUrl}`;
                                    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
                                    setShowToolbox(false);
                                }}
                                className="w-full flex items-center gap-3 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-all outline-none"
                            >
                                <div className="w-8 h-8 bg-[#064e3b] rounded-[0.4rem] flex items-center justify-center shrink-0 text-[#1DB954]">
                                    <MessageCircle className="w-4 h-4" />
                                </div>
                                <div className="text-left text-[14px] text-[#e2e8f0]">
                                    WhatsApp teilen
                                </div>
                            </button>

                            <button 
                                onClick={() => { setShowKindleModal(true); setShowToolbox(false); }}
                                className="w-full flex items-center gap-3 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-all outline-none"
                            >
                                <div className="w-8 h-8 bg-[#1e3a8a] rounded-[0.4rem] flex items-center justify-center shrink-0 text-[#60a5fa]">
                                    <Send className="w-4 h-4 ml-0.5 mt-0.5" />
                                </div>
                                <div className="text-left text-[14px] text-[#e2e8f0]">
                                    Kindle Export
                                </div>
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Re-voice Modal */}
            {showRevoiceModal && story && (
                <div className="fixed inset-0 z-[130] flex items-center justify-center p-4 bg-background/80 backdrop-blur-md">
                    <div className="bg-surface/90 backdrop-blur-2xl rounded-[2.5rem] w-full max-w-md shadow-2xl border border-slate-800/50 overflow-hidden animate-in fade-in zoom-in duration-300">
                        <div className="p-6">
                            <div className="flex items-center justify-between mb-6">
                                <h2 className="text-xl font-bold text-text flex items-center gap-2">
                                    <Mic className="w-5 h-5 text-primary" />
                                    Neu vertonen
                                </h2>
                                <button
                                    onClick={() => { setShowRevoiceModal(false); setConfirmRevoice(false); }}
                                    className="p-2 text-slate-500 hover:text-slate-300 rounded-full hover:bg-slate-800"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            {!confirmRevoice ? (
                                <>
                                    <p className="text-sm text-slate-400 mb-4">Wähle eine neue Stimme für diese Geschichte:</p>
                                    <div className="grid grid-cols-1 gap-2 max-h-[300px] overflow-y-auto mb-6 pr-1 custom-scrollbar">
                                        {/* Voices list - assuming 'voices' are in store or can be fetched */}
                                        {useStore.getState().voices.filter(v => v.key !== 'none').map(v => (
                                            <div
                                                key={v.key}
                                                className={`p-3 rounded-xl transition-all border-2 cursor-pointer flex items-center justify-between ${selectedVoice === v.key
                                                    ? 'border-primary bg-accent/20 shadow-sm'
                                                    : 'border-slate-800 bg-surface hover:border-slate-700'
                                                    }`}
                                                onClick={() => setSelectedVoice(v.key)}
                                            >
                                                <div className="flex items-center gap-3">
                                                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${selectedVoice === v.key ? 'bg-primary/20 text-primary' : 'bg-slate-900 text-slate-700'}`}>
                                                        <User className="w-4 h-4" />
                                                    </div>
                                                    <div>
                                                        <div className={`text-xs font-bold ${selectedVoice === v.key ? 'text-text' : 'text-slate-400'}`}>
                                                            {voiceName(v.key)}
                                                        </div>
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); handlePreviewVoice(v.key); }}
                                                    className={`w-7 h-7 rounded-full flex items-center justify-center transition-all ${previewVoice === v.key
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
                                            onClick={() => setShowRevoiceModal(false)}
                                            className="flex-1 px-4 py-3 border-2 border-slate-800 rounded-xl font-bold text-slate-500 hover:bg-surface transition-all"
                                        >
                                            Abbrechen
                                        </button>
                                        <button
                                            onClick={() => setConfirmRevoice(true)}
                                            className="btn-primary flex-1 px-4 py-3 shadow-lg shadow-primary/20"
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
                                    <p className="text-sm text-slate-400 mb-8 px-4">
                                        Die Geschichte wird mit der Stimme <strong>{voiceName(selectedVoice)}</strong> neu vertont.
                                    </p>
                                    <div className="flex flex-col gap-3">
                                        <button
                                            onClick={handleRevoice}
                                            disabled={isRevoicing}
                                            className="btn-primary w-full py-4 text-white font-bold rounded-2xl shadow-xl shadow-primary/20 hover:bg-emerald-600 transition-all flex items-center justify-center gap-3"
                                        >
                                            {isRevoicing ? <Loader2 className="w-5 h-5 animate-spin" /> : <Mic className="w-5 h-5" />}
                                            Jetzt starten
                                        </button>
                                        <button
                                            onClick={() => setConfirmRevoice(false)}
                                            disabled={isRevoicing}
                                            className="w-full py-3 text-sm font-bold text-slate-500 hover:text-slate-300 transition-colors"
                                        >
                                            Zurück zur Auswahl
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            <audio ref={audioRef} className="hidden" />
        </div>
    );
}

import { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { fetchStory, getThumbUrl, type StoryDetail, exportStoryToKindle } from '../lib/api';
import { 
    Moon, BookOpen, Send, Loader2, MessageCircle, Headphones, Heart
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function ReaderLayer() {
    const { 
        isReaderOpen, readerStoryId, setAudioCompanion, user,
        toggleFavorite, showAudioCompanion
    } = useStore();
    const [story, setStory] = useState<StoryDetail | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isExporting, setIsExporting] = useState(false);
    const [showKindleModal, setShowKindleModal] = useState(false);
    const [kindleEmail, setKindleEmail] = useState<string>(() => user?.kindle_email || localStorage.getItem('kindle_email') || '');

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
        <div className="fixed inset-0 z-40 bg-background overflow-y-auto animate-in slide-in-from-bottom duration-300 ease-out">

            <div className="p-4 sm:p-6 max-w-2xl mx-auto pb-32">
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
                            <h1 className="text-3xl font-bold text-text font-serif leading-tight">{story.title}</h1>
                            
                            <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 mt-4 text-[11px] font-medium text-slate-500 uppercase tracking-wider font-mono">
                                {story.genre && (
                                    <span className="text-primary bg-accent/20 px-2 py-0.5 rounded text-[10px]">{story.genre}</span>
                                )}
                                <span className="flex items-center gap-1">
                                    <BookOpen className="w-3.5 h-3.5" />
                                    {story.word_count ? `${story.word_count} Worte` : 'Buch'}
                                </span>
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
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
                    <div className="bg-surface rounded-[2.5rem] w-full max-w-sm p-8 shadow-2xl border border-slate-800 animate-in zoom-in duration-200">
                        <h2 className="text-2xl font-bold text-text mb-2 font-serif">An Kindle senden</h2>
                        <p className="text-sm text-slate-500 mb-6 font-mono uppercase tracking-wider text-[10px]">E-Book Export</p>
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
                className={`fixed right-6 z-50 transition-all duration-500 ease-in-out ${
                    showAudioCompanion ? 'bottom-[148px]' : 'bottom-6'
                }`}
            >
                <button
                    onClick={() => story && toggleFavorite(story.id)}
                    className={`w-14 h-14 rounded-full flex items-center justify-center shadow-2xl backdrop-blur-md border transition-all active:scale-90 group ${
                        story?.is_favorite
                        ? 'bg-red-500/20 border-red-500/50 text-red-500'
                        : 'bg-slate-900/40 border-slate-700/50 text-slate-400 hover:text-red-400 hover:border-red-400/30'
                    }`}
                    aria-label={story?.is_favorite ? "Von Favoriten entfernen" : "Zu Favoriten hinzufügen"}
                >
                    <Heart className={`w-7 h-7 transition-transform group-hover:scale-110 ${story?.is_favorite ? 'fill-current animate-pulse-subtle' : ''}`} />
                </button>
            </div>
        </div>
    );
}

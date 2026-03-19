import { useEffect, useMemo } from 'react';
import { useStore } from '../store/useStore';
import { Trash2, ExternalLink, Clock, User as UserIcon, Loader2, Music, X, BookOpen } from 'lucide-react';
import toast from 'react-hot-toast';
import { useState, useRef } from 'react';
import ConfirmModal from './ConfirmModal';

interface Props {
    filterUserId: string | null;
    onClearFilter: () => void;
}

export default function AdminStoryManagement({ filterUserId, onClearFilter }: Props) {
    const { 
        stories, loadStories, deleteAdminStory, setReaderOpen, setRevoiceStoryId, 
        isLoading, adminUsers, loadMoreStories, hasMore 
    } = useStore();
    const [deleteConfirm, setDeleteConfirm] = useState<{ id: string, title: string } | null>(null);

    useEffect(() => {
        // Load stories for specific user or all if filter is null
        loadStories(1, filterUserId || undefined, 20); 
    }, [loadStories, filterUserId]);

    const observerTarget = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const observer = new IntersectionObserver(
            entries => {
                if (entries[0].isIntersecting && hasMore && !isLoading) {
                    loadMoreStories(filterUserId || undefined, 20);
                }
            },
            { threshold: 0.1, rootMargin: '100px' }
        );

        if (observerTarget.current) {
            observer.observe(observerTarget.current);
        }

        return () => observer.disconnect();
    }, [hasMore, isLoading, loadMoreStories, filterUserId]);

    const filteredUserName = useMemo(() => {
        if (!filterUserId) return null;
        const user = adminUsers.find(u => u.id === filterUserId);
        return user ? (user.username || user.email) : 'Unbekannter Nutzer';
    }, [adminUsers, filterUserId]);

    const handleDelete = async (id: string, title: string) => {
        setDeleteConfirm({ id, title });
    };

    const confirmDelete = async () => {
        if (!deleteConfirm) return;
        const { id } = deleteConfirm;
        try {
            await deleteAdminStory(id);
            toast.success('Geschichte gelöscht');
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Löschen');
        } finally {
            setDeleteConfirm(null);
        }
    };

    const formatDuration = (seconds: number | null) => {
        if (!seconds) return '--:--';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    if (isLoading && stories.length === 0) {
        return (
            <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {filterUserId && (
                <div className="flex items-center justify-between px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl mb-4">
                    <span className="text-sm text-emerald-400">
                        Gefiltert nach: <strong className="text-white">{filteredUserName}</strong>
                    </span>
                    <button 
                        onClick={onClearFilter}
                        className="p-1 hover:bg-white/10 rounded-lg transition-all text-slate-400 hover:text-white"
                        title="Filter aufheben"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            )}

            {stories.map((story) => (
                <div key={story.id} className="glass-panel rounded-2xl p-4 flex items-center justify-between group">
                    <div className="flex items-center gap-4 flex-1 min-w-0">
                        <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center flex-shrink-0 overflow-hidden relative">
                            {story.image_url ? (
                                <img src={story.image_url} alt="" className="w-full h-full object-cover opacity-60 group-hover:opacity-80 transition-opacity" />
                            ) : (
                                <BookOpen className="w-6 h-6 text-slate-600" />
                            )}
                        </div>
                        <div className="flex flex-col min-w-0">
                            <span className="text-white font-medium truncate group-hover:text-emerald-400 transition-colors">
                                {story.title}
                            </span>
                            <div className="flex items-center gap-3 text-xs text-slate-500 uppercase tracking-wider">
                                <span className="flex items-center gap-1"><UserIcon className="w-3 h-3" /> {story.user_email || 'System'}</span>
                                <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {formatDuration(story.duration_seconds)}</span>
                                <span className="text-slate-600 italic">{new Date(story.created_at).toLocaleDateString()}</span>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setReaderOpen(true, story.id)}
                            className="p-2 text-slate-400 hover:text-emerald-500 hover:bg-emerald-500/10 rounded-lg transition-all"
                            title="Anzeigen"
                        >
                            <ExternalLink className="w-5 h-5" />
                        </button>
                        <button
                            onClick={() => setRevoiceStoryId(story.id)}
                            className="p-2 text-slate-400 hover:text-orange-400 hover:bg-orange-500/10 rounded-lg transition-all"
                            title="Neu vertonen"
                        >
                            <Music className="w-5 h-5" />
                        </button>
                        <button
                            onClick={() => handleDelete(story.id, story.title)}
                            className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-all"
                            title="Löschen"
                        >
                            <Trash2 className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            ))}

            {stories.length === 0 && !isLoading && (
                <div className="text-center py-12 text-slate-500 italic">
                    Keine Geschichten gefunden.
                </div>
            )}

            {/* Sentinel for Infinite Scroll */}
            <div ref={observerTarget} className="h-20 flex items-center justify-center">
                {isLoading && stories.length > 0 && (
                    <div className="flex flex-col items-center gap-2 animate-in fade-in duration-300">
                        <Loader2 className="w-6 h-6 text-emerald-500 animate-spin" />
                        <span className="text-xs uppercase tracking-widest text-slate-500 font-bold">Lade mehr...</span>
                    </div>
                )}
                {!hasMore && stories.length > 0 && (
                    <div className="text-xs uppercase tracking-widest text-slate-700 font-bold">
                        Alle Geschichten geladen
                    </div>
                )}
            </div>

            <ConfirmModal 
                isOpen={!!deleteConfirm}
                title="Geschichte löschen"
                message={`Möchtest du "${deleteConfirm?.title}" wirklich als Admin unwiderruflich löschen?`}
                onConfirm={confirmDelete}
                onClose={() => setDeleteConfirm(null)}
            />
        </div>
    );
}

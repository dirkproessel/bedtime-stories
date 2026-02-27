import { useStore } from '../store/useStore';
import { getAudioUrl, deleteStory } from '../lib/api';
import { Play, Trash2, Clock, BookOpen, Calendar } from 'lucide-react';
import toast from 'react-hot-toast';

export default function StoryArchive() {
    const { stories, setActiveView, setSelectedStoryId, loadStories } = useStore();

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
                            <div className="flex items-start justify-between gap-3">
                                <div className="flex-1 min-w-0" onClick={() => handlePlay(story.id)} style={{ cursor: 'pointer' }}>
                                    <h3 className="font-bold text-slate-900 truncate group-hover:text-indigo-600 transition-colors">
                                        {story.title}
                                    </h3>
                                    <p className="text-xs text-slate-400 mt-1 truncate">{story.description}</p>
                                    <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
                                        <span className="flex items-center gap-1">
                                            <Clock className="w-3 h-3" />
                                            {formatDuration(story.duration_seconds)}
                                        </span>
                                        <span className="flex items-center gap-1">
                                            <BookOpen className="w-3 h-3" />
                                            {story.chapter_count} Kapitel
                                        </span>
                                        <span className="flex items-center gap-1">
                                            <Calendar className="w-3 h-3" />
                                            {formatDate(story.created_at)}
                                        </span>
                                    </div>
                                </div>
                                <div className="flex items-center gap-1.5 shrink-0">
                                    <button
                                        onClick={() => handlePlay(story.id)}
                                        className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-500 flex items-center justify-center hover:bg-indigo-100 transition-colors"
                                    >
                                        <Play className="w-4 h-4 ml-0.5" />
                                    </button>
                                    <button
                                        onClick={() => handleDelete(story.id, story.title)}
                                        className="w-10 h-10 rounded-xl bg-slate-50 text-slate-300 flex items-center justify-center hover:bg-red-50 hover:text-red-400 transition-colors"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

import { useStore } from '../store/useStore';
import { deleteStory } from '../lib/api';
import { Play, Trash2, Clock, BookOpen, Calendar } from 'lucide-react';
import toast from 'react-hot-toast';

export default function StoryArchive() {
    const { stories, setActiveView, setSelectedStoryId, loadStories, updateStorySpotify } = useStore();

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
                                        <div className="flex-1 min-w-0 cursor-pointer" onClick={() => handlePlay(story.id)}>
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
                                    </div>
                                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-50">
                                        <div className="flex items-center gap-4">
                                            <button
                                                onClick={() => handlePlay(story.id)}
                                                className="flex items-center gap-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
                                            >
                                                <Play className="w-3.5 h-3.5" />
                                                Anhören
                                            </button>
                                            <label className="flex items-center gap-1.5 cursor-pointer group/toggle">
                                                <div className="relative">
                                                    <input
                                                        type="checkbox"
                                                        className="sr-only"
                                                        checked={story.is_on_spotify}
                                                        onChange={(e) => handleSpotifyToggle(story.id, e.target.checked)}
                                                    />
                                                    <div className={`w-8 h-4.5 rounded-full transition-colors ${story.is_on_spotify ? 'bg-green-500' : 'bg-slate-200'}`}></div>
                                                    <div className={`absolute top-0.5 left-0.5 w-3.5 h-3.5 bg-white rounded-full transition-transform ${story.is_on_spotify ? 'translate-x-3.5' : ''}`}></div>
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
        </div>
    );
}

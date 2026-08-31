import React, { useState, useEffect } from 'react';
import { Sparkles, Layers, X, BookOpen } from 'lucide-react';
import { AUTHORS } from '../lib/authors';
import { GENRES } from './StoryCreator';
import { createProSeries, fetchGenreProfile } from '../lib/api';
import { useStore } from '../store/useStore';
import toast from 'react-hot-toast';

interface SeriesWizardProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: (seriesDetail: any) => void;
}

export default function SeriesWizard({ isOpen, onClose, onSuccess }: SeriesWizardProps) {
    const { loadProSeries, loadProProjects, loadProProjectDetail } = useStore();

    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [genre, setGenre] = useState('Fantasy');
    const [style, setStyle] = useState('adams');
    const [plannedVolumes, setPlannedVolumes] = useState<number | ''>(3);
    const [autoInitVolume1, setAutoInitVolume1] = useState(true);

    // Genre specific configurations
    const [genreProfile, setGenreProfile] = useState<any>(null);
    const [selectedTropes, setSelectedTropes] = useState<string[]>([]);
    const [pov, setPov] = useState<string>('');
    const [spiceLevel, setSpiceLevel] = useState<number>(3);
    const [isKidsBook, setIsKidsBook] = useState(false);

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitStep, setSubmitStep] = useState('');

    useEffect(() => {
        if (!isOpen) return;
        const loadProfile = async () => {
            try {
                const profile = await fetchGenreProfile(genre);
                setGenreProfile(profile);
                setPov(profile.default_pov || '');
                setSelectedTropes([]);
                setSpiceLevel(3);
            } catch (err) {
                console.error(err);
                setGenreProfile(null);
            }
        };
        loadProfile();
    }, [genre, isOpen]);

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!title.trim() || !description.trim()) {
            toast.error('Bitte Serientitel und übergeordnete Prämisse ausfüllen');
            return;
        }

        const genreConfigJson = JSON.stringify({
            tropes: selectedTropes,
            pov: pov,
            spice_level: genreProfile?.has_spice_levels ? spiceLevel : null,
            is_kids_book: isKidsBook
        });

        setIsSubmitting(true);
        setSubmitStep(autoInitVolume1 ? 'Entwerfe Serien-Universum & Band 1...' : 'Erstelle Buch-Serie...');

        try {
            const newSeries = await createProSeries({
                title: title.trim(),
                description: description.trim(),
                genre,
                style,
                genre_config: genreConfigJson,
                planned_volumes: plannedVolumes === '' ? null : Number(plannedVolumes),
                auto_init_volume_1: autoInitVolume1
            });

            toast.success(autoInitVolume1 ? 'Serie & Band 1 erfolgreich initialisiert!' : 'Serie erfolgreich angelegt!');
            await loadProSeries();
            await loadProProjects();

            onClose();
            onSuccess(newSeries);

            // If volume 1 was created, open it in editor
            if (autoInitVolume1 && newSeries.books && newSeries.books.length > 0) {
                const vol1 = newSeries.books[0];
                await loadProProjectDetail(vol1.id);
            }
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Erstellen der Serie');
        } finally {
            setIsSubmitting(false);
            setSubmitStep('');
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md overflow-y-auto">
            <div className="bg-slate-900 border border-indigo-500/30 rounded-3xl p-6 sm:p-8 max-w-2xl w-full shadow-2xl space-y-6 animate-in fade-in zoom-in-95 duration-200 my-8">
                
                {/* Header */}
                <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
                            <Layers className="w-5 h-5" />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-white flex items-center gap-2">
                                Neue Buch-Serie starten
                                <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-medium">
                                    Franchise Mode
                                </span>
                            </h3>
                            <p className="text-xs text-text-muted mt-0.5">
                                Plane eine mehrteilige Buchreihe mit übergeordnetem Worldbuilding und Stammbesetzung.
                            </p>
                        </div>
                    </div>
                    <button 
                        onClick={onClose} 
                        disabled={isSubmitting}
                        className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition-colors disabled:opacity-50"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {isSubmitting ? (
                    <div className="py-16 text-center space-y-4">
                        <div className="relative w-16 h-16 mx-auto">
                            <div className="absolute inset-0 rounded-full bg-indigo-500/20 animate-ping" />
                            <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-xl shadow-indigo-500/30 animate-pulse">
                                <Sparkles className="w-8 h-8 animate-spin" style={{ animationDuration: '4s' }} />
                            </div>
                        </div>
                        <div className="space-y-1">
                            <h4 className="text-lg font-semibold text-white">{submitStep}</h4>
                            <p className="text-xs text-indigo-300/70">
                                KI generiert Serien-Lore, Master-Charakter-Bibel und Cover-Styleguide...
                            </p>
                        </div>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-5">
                        
                        {/* Title & Volume Count */}
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <div className="sm:col-span-2 space-y-1.5">
                                <label className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                                    Serientitel *
                                </label>
                                <input 
                                    type="text" 
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    placeholder="z. B. Die Chroniken von Eldoria, Leo & Mia Detektive..."
                                    required
                                    className="w-full bg-surface border border-slate-700 rounded-xl px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                                />
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                                    Geplante Bände
                                </label>
                                <select 
                                    value={plannedVolumes}
                                    onChange={(e) => setPlannedVolumes(e.target.value === '' ? '' : Number(e.target.value))}
                                    className="w-full bg-surface border border-slate-700 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors"
                                >
                                    <option value={3}>Trilogie (3 Bände)</option>
                                    <option value={4}>4 Bände</option>
                                    <option value={5}>Pentalogie (5 Bände)</option>
                                    <option value={7}>7 Bände</option>
                                    <option value="">Offene / Fortlaufende Reihe</option>
                                </select>
                            </div>
                        </div>

                        {/* Series Premise / Description */}
                        <div className="space-y-1.5">
                            <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                                Übergeordnete Serien-Prämisse & Kernkonflikt *
                            </label>
                            <textarea 
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                placeholder="Worum geht es in der gesamten Serie? Was ist die Welt, der Hauptkonflikt, wer sind die Hauptfiguren und was ist das große Ziel über alle Bände hinweg?"
                                required
                                rows={4}
                                className="w-full bg-surface border border-slate-700 rounded-xl px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
                            />
                        </div>

                        {/* Genre & Style */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                                <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                                    Genre
                                </label>
                                <select 
                                    value={genre}
                                    onChange={(e) => setGenre(e.target.value)}
                                    className="w-full bg-surface border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors"
                                >
                                    {GENRES.map(g => (
                                        <option key={g.value} value={g.value}>{g.label}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                                    Autorenstil
                                </label>
                                <select 
                                    value={style}
                                    onChange={(e) => setStyle(e.target.value)}
                                    className="w-full bg-surface border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors"
                                >
                                    {AUTHORS.map(a => (
                                        <option key={a.id} value={a.id}>{a.name} ({a.desc})</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        {/* Kinderbuch Mode toggle */}
                        <div className="p-3 bg-surface/80 rounded-2xl border border-slate-800 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <span className="text-xl">🧒</span>
                                <div>
                                    <h4 className="text-sm font-semibold text-white">Kinderbuch-Reihe</h4>
                                    <p className="text-xs text-text-muted">Kindgerechte Sprache, gewaltfrei, Identifikationsfiguren für junge Leser.</p>
                                </div>
                            </div>
                            <input 
                                type="checkbox"
                                checked={isKidsBook}
                                onChange={(e) => setIsKidsBook(e.target.checked)}
                                className="w-5 h-5 accent-indigo-600 rounded cursor-pointer"
                            />
                        </div>

                        {/* Auto init Volume 1 Option */}
                        <div className="p-3.5 bg-indigo-950/30 rounded-2xl border border-indigo-500/20 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-300">
                                    <BookOpen className="w-4 h-4" />
                                </div>
                                <div>
                                    <h4 className="text-sm font-semibold text-white">Band 1 sofort automatisch mitkonzipieren</h4>
                                    <p className="text-xs text-indigo-300/70">
                                        Erstellt direkt das erste Buchprojekt mit verknüpfter Master-Bibel & öffnet den Editor.
                                    </p>
                                </div>
                            </div>
                            <input 
                                type="checkbox"
                                checked={autoInitVolume1}
                                onChange={(e) => setAutoInitVolume1(e.target.checked)}
                                className="w-5 h-5 accent-indigo-600 rounded cursor-pointer"
                            />
                        </div>

                        {/* Actions */}
                        <div className="flex justify-end gap-3 pt-2">
                            <button 
                                type="button"
                                onClick={onClose}
                                className="px-5 py-2.5 bg-surface hover:bg-slate-800 text-slate-300 rounded-xl text-sm font-medium transition-colors border border-slate-700"
                            >
                                Abbrechen
                            </button>
                            <button 
                                type="submit"
                                className="px-6 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl text-sm font-semibold shadow-lg shadow-indigo-500/25 flex items-center gap-2 transition-all"
                            >
                                <Sparkles className="w-4 h-4" />
                                Serie erschaffen
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}

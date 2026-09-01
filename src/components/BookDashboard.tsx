import React, { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { Plus, BookOpen, Trash2, ArrowRight, Loader2, RefreshCw, ArrowLeft, Layers, Sparkles, ChevronRight } from 'lucide-react';
import BookEditor from './BookEditor';
import SeriesWizard from './SeriesWizard';
import SeriesView from './SeriesView';
import AnthologyWizard from './AnthologyWizard';
import { createProBook, deleteProBook, fetchGenreProfile } from '../lib/api';
import toast from 'react-hot-toast';
import { AUTHORS, formatAuthorStyles } from '../lib/authors';
import { GENRES } from './StoryCreator';

export default function BookDashboard() {
    const { 
        proProjects, 
        currentProProject, 
        setCurrentProProject, 
        loadProProjects, 
        loadProProjectDetail,
        proSeries,
        currentProSeries,
        setCurrentProSeries,
        loadProSeries,
        loadProSeriesDetail,
        deleteProSeries,
        isLoading,
        setActiveView
    } = useStore();
    
    const [dashboardTab, setDashboardTab] = useState<'books' | 'series'>('books');
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showSeriesWizard, setShowSeriesWizard] = useState(false);
    const [showAnthologyWizard, setShowAnthologyWizard] = useState(false);

    const [title, setTitle] = useState('');
    const [prompt, setPrompt] = useState('');
    const [genre, setGenre] = useState('Fantasy');
    const [selectedAuthors, setSelectedAuthors] = useState<string[]>(['adams']);
    const [language, setLanguage] = useState<'de' | 'en'>('de');
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Genre specific configurations
    const [genreProfile, setGenreProfile] = useState<any>(null);
    const [selectedTropes, setSelectedTropes] = useState<string[]>([]);
    const [pov, setPov] = useState<string>('');
    const [spiceLevel, setSpiceLevel] = useState<number>(3);

    // Initial load
    useEffect(() => {
        loadProProjects();
        loadProSeries();
    }, []);

    // Simple status polling if any project is in "generating" status
    useEffect(() => {
        const interval = setInterval(async () => {
            const hasGenerating = useStore.getState().proProjects.some(p => p.status === 'generating');
            if (hasGenerating) {
                try {
                    const { fetchProBooks } = await import('../lib/api');
                    const proProjects = await fetchProBooks();
                    useStore.setState({ proProjects });
                } catch (e) {
                    console.error('Polling failed:', e);
                }
            }
        }, 3000);

        return () => clearInterval(interval);
    }, []);

    // Load genre profile when genre or modal changes
    useEffect(() => {
        if (!showCreateModal) return;
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
    }, [genre, showCreateModal]);

    const handleCreateProject = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!title.trim() || !prompt.trim()) {
            toast.error('Bitte Titel und Beschreibung ausfüllen');
            return;
        }

        const genreConfigJson = JSON.stringify({
            tropes: selectedTropes,
            pov: pov,
            spice_level: genreProfile?.has_spice_levels ? spiceLevel : null
        });

        const styleString = selectedAuthors.length > 0 ? selectedAuthors.join(',') : 'adams';

        setIsSubmitting(true);
        try {
            const newProject = await createProBook({ 
                title, 
                prompt, 
                genre, 
                style: styleString, 
                language,
                genre_config: genreConfigJson 
            });
            toast.success('Projekt erfolgreich angelegt!');
            setTitle('');
            setPrompt('');
            setLanguage('de');
            setShowCreateModal(false);
            
            // Immediately open the newly created project
            await loadProProjectDetail(newProject.id);
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Anlegen');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleDeleteProject = async (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!window.confirm('Möchtest du dieses Projekt wirklich unwiderruflich löschen?')) return;
        
        try {
            await deleteProBook(id);
            toast.success('Projekt gelöscht');
            loadProProjects();
            loadProSeries();
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Löschen');
        }
    };

    const handleDeleteSeries = async (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!window.confirm('Möchtest du diese Serie wirklich auflösen? Die Bücher bleiben als Einzelbände erhalten.')) return;
        
        try {
            await deleteProSeries(id);
            toast.success('Serie aufgelöst');
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Löschen');
        }
    };

    const handleOpenProject = async (id: string) => {
        try {
            await loadProProjectDetail(id);
        } catch (e: any) {
            toast.error('Fehler beim Laden des Projekts: ' + e.message);
        }
    };

    const handleOpenSeries = async (id: string) => {
        try {
            await loadProSeriesDetail(id);
        } catch (e: any) {
            toast.error('Fehler beim Laden der Serie: ' + e.message);
        }
    };

    // If viewing a single project editor
    if (currentProProject) {
        return (
            <BookEditor 
                project={currentProProject} 
                onBack={() => {
                    setCurrentProProject(null);
                    loadProProjects();
                    loadProSeries();
                }} 
            />
        );
    }

    // If viewing a Series hub
    if (currentProSeries) {
        return (
            <SeriesView 
                series={currentProSeries} 
                onBack={() => {
                    setCurrentProSeries(null);
                    loadProSeries();
                    loadProProjects();
                }} 
            />
        );
    }

    return (
        <div className="space-y-6">
            
            {/* Header Section */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-5">
                <div className="flex items-center gap-4">
                    <button 
                        onClick={() => setActiveView('create')}
                        className="p-2.5 bg-surface hover:bg-slate-800 text-slate-400 hover:text-white rounded-xl transition-colors border border-slate-800"
                        title="Zurück zum Labor"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </button>
                    <div>
                        <h2 className="text-xl font-bold text-white flex items-center gap-2">
                            Storyja Pro Studio
                            <span className="text-xs px-2 py-0.5 rounded-full bg-primary/20 text-primary border border-primary/30 font-medium">
                                Pro
                            </span>
                        </h2>
                        <p className="text-xs text-text-muted mt-1">
                            Erstelle lange Novellen, professionelle E-Books und mehrteilige Buchreihen.
                        </p>
                    </div>
                </div>
                
                <div className="flex items-center gap-2">
                    <button 
                        onClick={() => { loadProProjects(); loadProSeries(); }} 
                        className="p-2.5 bg-surface rounded-xl hover:bg-slate-800 text-slate-300 transition-colors border border-slate-800"
                        title="Aktualisieren"
                    >
                        <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                    </button>
                    
                    <button 
                        onClick={() => setShowSeriesWizard(true)}
                        className="px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl text-sm font-semibold shadow-lg shadow-indigo-500/20 flex items-center gap-2 transition-all"
                    >
                        <Sparkles className="w-4 h-4" />
                        + Neue Buch-Serie
                    </button>

                    <button 
                        onClick={() => setShowAnthologyWizard(true)}
                        className="px-4 py-2.5 bg-gradient-to-r from-amber-600 to-primary hover:from-amber-500 hover:to-primary-hover text-white rounded-xl text-sm font-semibold shadow-lg shadow-amber-500/20 flex items-center gap-2 transition-all"
                    >
                        <Layers className="w-4 h-4" />
                        + Kurzgeschichten-Sammelband
                    </button>

                    <button 
                        onClick={() => setShowCreateModal(true)}
                        className="btn-primary py-2.5 px-4 text-sm flex items-center gap-2 rounded-xl"
                    >
                        <Plus className="w-4 h-4" />
                        Neues Einzelbuch
                    </button>
                </div>
            </div>

            {/* Dashboard Tabs: Einzelbände vs. Serien */}
            <div className="flex gap-3 border-b border-slate-800/80 pb-3">
                <button
                    onClick={() => setDashboardTab('books')}
                    className={`px-4 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 transition-all ${
                        dashboardTab === 'books'
                            ? 'bg-slate-800 text-white shadow'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                    }`}
                >
                    <BookOpen className="w-4 h-4" />
                    Alle Buchprojekte ({proProjects.length})
                </button>

                <button
                    onClick={() => setDashboardTab('series')}
                    className={`px-4 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 transition-all ${
                        dashboardTab === 'series'
                            ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/25'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                    }`}
                >
                    <Layers className="w-4 h-4" />
                    Buch-Serien & Trilogien ({proSeries.length})
                </button>
            </div>

            {/* TAB: SERIES */}
            {dashboardTab === 'series' && (
                <div className="space-y-4">
                    {proSeries.length === 0 ? (
                        <div className="text-center py-20 bg-surface/40 border border-slate-800 rounded-3xl space-y-4">
                            <Layers className="w-12 h-12 text-slate-600 mx-auto" />
                            <div>
                                <h3 className="text-white font-medium">Bislang keine Buch-Serien angelegt</h3>
                                <p className="text-xs text-text-muted mt-1">
                                    Starte deine erste mehrteilige Reihe mit fortlaufenden Charakteren und konsistentem Cover-Design!
                                </p>
                            </div>
                            <button
                                onClick={() => setShowSeriesWizard(true)}
                                className="px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl text-xs font-semibold inline-flex items-center gap-2 shadow-lg shadow-indigo-500/20"
                            >
                                <Sparkles className="w-4 h-4" />
                                Erste Buch-Serie starten
                            </button>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                            {proSeries.map((s) => {
                                return (
                                    <div
                                        key={s.id}
                                        onClick={() => handleOpenSeries(s.id)}
                                        className="group bg-surface/70 hover:bg-surface border border-slate-800 hover:border-indigo-500/40 rounded-3xl p-5 transition-all duration-200 cursor-pointer shadow-lg hover:shadow-indigo-500/10 flex flex-col justify-between space-y-4 relative"
                                    >
                                        <div className="space-y-3">
                                            <div className="flex items-start justify-between gap-3">
                                                <div className="flex items-center gap-2">
                                                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1">
                                                        <Layers className="w-3 h-3" />
                                                        Serie
                                                    </span>
                                                    <span className="text-[10px] text-slate-400 font-mono">
                                                        {s.language === 'en' ? '🇬🇧 EN' : '🇩🇪 DE'} &bull; {s.genre}
                                                    </span>
                                                </div>

                                                <button 
                                                    onClick={(e) => handleDeleteSeries(s.id, e)}
                                                    className="text-slate-500 hover:text-rose-400 p-1 hover:bg-rose-500/10 rounded-lg transition-colors"
                                                    title="Serie auflösen"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>

                                            <h3 className="text-base font-bold text-white group-hover:text-indigo-300 transition-colors line-clamp-1">
                                                {s.title}
                                            </h3>

                                            <p className="text-xs text-text-muted line-clamp-2 leading-relaxed">
                                                {s.description}
                                            </p>
                                        </div>

                                        <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                                            <span className="font-semibold text-slate-300">
                                                {s.book_count || 0} {s.planned_volumes ? `von ${s.planned_volumes} Bänden` : 'Bände'}
                                            </span>

                                            <span className="flex items-center text-indigo-400 font-semibold group-hover:translate-x-0.5 transition-transform">
                                                Serie öffnen <ChevronRight className="w-4 h-4 ml-0.5" />
                                            </span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}

            {/* TAB: ALL BOOKS */}
            {dashboardTab === 'books' && (
                <div className="space-y-4">
                    {proProjects.length === 0 ? (
                        <div className="text-center py-20 bg-surface/50 border border-slate-800 rounded-3xl space-y-4">
                            <BookOpen className="w-12 h-12 text-slate-600 mx-auto" />
                            <div>
                                <h3 className="text-white font-medium">Bislang keine Buchprojekte vorhanden</h3>
                                <p className="text-xs text-text-muted mt-1">Klicke auf 'Neues Einzelbuch' oder 'Kurzgeschichten-Sammelband' um zu starten.</p>
                            </div>
                            <div className="flex justify-center gap-3 pt-2">
                                <button
                                    onClick={() => setShowAnthologyWizard(true)}
                                    className="px-4 py-2 bg-gradient-to-r from-amber-600 to-primary text-white rounded-xl text-xs font-semibold inline-flex items-center gap-2 shadow-lg shadow-amber-500/20"
                                >
                                    <Layers className="w-3.5 h-3.5" />
                                    Kurzgeschichten zu Sammelband bündeln
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {proProjects.map((p) => {
                                const isGenerating = p.status === 'generating';
                                return (
                                    <div 
                                        key={p.id}
                                        onClick={() => handleOpenProject(p.id)}
                                        className="bg-surface hover:bg-slate-800/80 p-5 rounded-3xl border border-slate-800 hover:border-slate-700/80 cursor-pointer transition-all flex flex-col justify-between h-56 group relative"
                                    >
                                        <div className="space-y-2">
                                            <div className="flex justify-between items-start gap-4">
                                                <div>
                                                    {p.is_anthology && (
                                                        <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider block mb-0.5 flex items-center gap-1">
                                                            <Layers className="w-3 h-3" />
                                                            Sammelband / Anthologie
                                                        </span>
                                                    )}
                                                    {p.series_id && (
                                                        <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider block mb-0.5">
                                                            {p.series_subtitle || 'Serie'}
                                                        </span>
                                                    )}
                                                    <h3 className="font-semibold text-white text-base group-hover:text-primary transition-colors line-clamp-1">
                                                        {p.title}
                                                    </h3>
                                                </div>
                                                <button 
                                                    onClick={(e) => handleDeleteProject(p.id, e)}
                                                    className="text-slate-500 hover:text-red-400 p-1 hover:bg-red-500/10 rounded-lg transition-colors shrink-0"
                                                    title="Projekt löschen"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>
                                            
                                            <p className="text-xs text-text-muted line-clamp-3 leading-relaxed">
                                                {p.prompt}
                                            </p>
                                        </div>

                                        <div className="mt-4 border-t border-slate-800/80 pt-4 flex justify-between items-center text-xs">
                                            <div className="flex flex-col gap-1">
                                                <span className="text-[10px] uppercase font-mono text-slate-500">
                                                    {p.language === 'en' ? '🇬🇧 EN' : '🇩🇪 DE'} &bull; {p.genre} &bull; {formatAuthorStyles(p.style)}
                                                </span>
                                                {isGenerating ? (
                                                    <span className="text-primary font-medium flex items-center gap-1.5">
                                                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                        {p.progress || 'Generiere...'} ({p.progress_pct}%)
                                                    </span>
                                                ) : p.status === 'error' ? (
                                                    <span className="text-red-400 font-medium line-clamp-1 max-w-[200px]">
                                                        Fehler: {p.progress}
                                                    </span>
                                                ) : (
                                                    <span className="text-slate-400">
                                                        Status: <b className="text-slate-300 font-medium capitalize">{p.status}</b>
                                                    </span>
                                                )}
                                            </div>

                                            <div className="w-8 h-8 rounded-xl bg-slate-800 flex items-center justify-center text-slate-400 group-hover:text-primary group-hover:bg-primary/10 transition-colors">
                                                <ArrowRight className="w-4 h-4" />
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}

            {/* Anthology Wizard Modal */}
            <AnthologyWizard
                isOpen={showAnthologyWizard}
                onClose={() => setShowAnthologyWizard(false)}
                onCreated={(newBook) => {
                    loadProProjects();
                    loadProProjectDetail(newBook.id);
                }}
            />

            {/* Series Wizard Modal */}
            <SeriesWizard 
                isOpen={showSeriesWizard}
                onClose={() => setShowSeriesWizard(false)}
                onSuccess={(newSeries) => {
                    setCurrentProSeries(newSeries);
                }}
            />

            {/* Create Project Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-[1000] flex items-center justify-center p-4">
                    <div className="bg-surface border border-slate-800 w-full max-w-lg rounded-3xl p-6 shadow-2xl relative space-y-4">
                        <div className="space-y-1">
                            <h3 className="text-lg font-bold text-white">Neues Buchprojekt</h3>
                            <p className="text-xs text-text-muted">Lege den Grundstein für deine neue Novelle.</p>
                        </div>

                        <form onSubmit={handleCreateProject} className="space-y-4">
                            <div className="space-y-1">
                                <label className="text-xs font-medium text-slate-300">Titel des Buches</label>
                                <input 
                                    type="text" 
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    className="w-full bg-background border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-primary"
                                    placeholder="z. B. Die Chroniken der Kaffeemaschine"
                                />
                            </div>

                            <div className="space-y-1">
                                <label className="text-xs font-medium text-slate-300">Sprache des Buches</label>
                                <div className="grid grid-cols-2 gap-2">
                                    <button
                                        type="button"
                                        onClick={() => setLanguage('de')}
                                        className={`py-2 px-3 rounded-xl border text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                                            language === 'de'
                                                ? 'bg-primary/20 border-primary text-primary'
                                                : 'bg-background border-slate-800 text-slate-400 hover:border-slate-700'
                                        }`}
                                    >
                                        <span>🇩🇪</span> Deutsch
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setLanguage('en')}
                                        className={`py-2 px-3 rounded-xl border text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                                            language === 'en'
                                                ? 'bg-primary/20 border-primary text-primary'
                                                : 'bg-background border-slate-800 text-slate-400 hover:border-slate-700'
                                        }`}
                                    >
                                        <span>🇬🇧</span> English
                                    </button>
                                </div>
                            </div>

                            <div className="space-y-1">
                                <label className="text-xs font-medium text-slate-300">Konzept / Kernidee</label>
                                <textarea 
                                    value={prompt}
                                    onChange={(e) => setPrompt(e.target.value)}
                                    rows={4}
                                    className="w-full bg-background border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-primary resize-none"
                                    placeholder={language === 'en' ? "What is the book about? Premise, characters, plot twists..." : "Worum soll es in dem Buch gehen? Details zur Handlung, Überraschungen, roter Faden..."}
                                />
                            </div>

                                <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1">
                                    <label className="text-xs font-medium text-slate-300">Genre</label>
                                    <select 
                                        value={genre}
                                        onChange={(e) => setGenre(e.target.value)}
                                            className="w-full bg-background border border-slate-800 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary"
                                        >
                                            {GENRES.map(g => (
                                                <option key={g.value} value={g.value}>{g.label}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="space-y-1">
                                        <div className="flex justify-between items-center">
                                            <label className="text-xs font-medium text-slate-300">Autorenstil (Mixe bis zu 3)</label>
                                            <span className="text-[10px] text-primary font-bold">{selectedAuthors.length}/3 gewählt</span>
                                        </div>
                                        <div className="max-h-36 overflow-y-auto bg-background border border-slate-800 rounded-xl p-2 space-y-1 no-scrollbar">
                                            {AUTHORS.map(a => {
                                                const isSelected = selectedAuthors.includes(a.id);
                                                const authorIndex = selectedAuthors.indexOf(a.id);
                                                return (
                                                    <div 
                                                        key={a.id}
                                                        onClick={() => {
                                                            if (isSelected) {
                                                                setSelectedAuthors(selectedAuthors.filter(id => id !== a.id));
                                                            } else if (selectedAuthors.length < 3) {
                                                                setSelectedAuthors([...selectedAuthors, a.id]);
                                                            } else {
                                                                toast('Maximal 3 Autoren können für den Stil kombiniert werden', { icon: 'ℹ️' });
                                                            }
                                                        }}
                                                        className={`p-1.5 rounded-lg border text-xs cursor-pointer flex items-center justify-between transition-all ${
                                                            isSelected 
                                                                ? 'bg-primary/15 border-primary text-white font-medium shadow-sm' 
                                                                : 'border-slate-800/80 bg-slate-900/40 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                                                        }`}
                                                    >
                                                        <div className="min-w-0">
                                                            <div className="text-[11px] font-semibold truncate">{a.name}</div>
                                                            <div className="text-[9px] text-slate-500 truncate">{a.desc}</div>
                                                        </div>
                                                        {isSelected && (
                                                            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-primary/30 text-primary border border-primary/40 shrink-0">
                                                                {authorIndex === 0 ? '1. Wortwahl' : authorIndex === 1 ? '2. Atmosphäre' : '3. Erzählweise'}
                                                            </span>
                                                        )}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                </div>

                            {/* Genre-spezifische Einstellungen (Tropes, POV, Spice) */}
                            {genreProfile && (
                                <div className="space-y-4 border-t border-slate-800/80 pt-4">
                                    {/* Tropes */}
                                    {genreProfile.available_tropes?.length > 0 && (
                                        <div className="space-y-2">
                                            <label className="text-xs font-medium text-slate-300">
                                                Aktive Tropes (wähle passende narrative Elemente)
                                            </label>
                                            <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto pr-1">
                                                {genreProfile.available_tropes.map((t: any) => {
                                                    const isSelected = selectedTropes.includes(t.id);
                                                    return (
                                                        <button
                                                            key={t.id}
                                                            type="button"
                                                            onClick={() => {
                                                                if (isSelected) {
                                                                    setSelectedTropes(selectedTropes.filter(id => id !== t.id));
                                                                } else {
                                                                    setSelectedTropes([...selectedTropes, t.id]);
                                                                }
                                                            }}
                                                            className={`text-[11px] px-2.5 py-1 rounded-full border transition-all ${
                                                                isSelected 
                                                                ? 'bg-primary/20 border-primary text-primary' 
                                                                : 'bg-background border-slate-800 text-slate-400 hover:border-slate-700'
                                                            }`}
                                                            title={t.description}
                                                        >
                                                            {t.name}
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}

                                    {/* POV */}
                                    {genreProfile.pov_options?.length > 0 && (
                                        <div className="space-y-2">
                                            <label className="text-xs font-medium text-slate-300">Erzählperspektive (POV)</label>
                                            <div className="grid grid-cols-2 gap-2">
                                                {genreProfile.pov_options.map((p: any) => (
                                                    <button
                                                        key={p.id}
                                                        type="button"
                                                        onClick={() => setPov(p.id)}
                                                        className={`text-[11px] p-2 rounded-xl border text-left transition-all flex flex-col justify-between ${
                                                            pov === p.id 
                                                            ? 'bg-primary/10 border-primary text-white' 
                                                            : 'bg-background border-slate-800 text-slate-400 hover:border-slate-700'
                                                        }`}
                                                    >
                                                        <span className="font-semibold text-slate-200">{p.name}</span>
                                                        <span className="text-[9px] text-text-muted mt-1 leading-snug">{p.description}</span>
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Spice Level */}
                                    {genreProfile.has_spice_levels && (
                                        <div className="space-y-2">
                                            <div className="flex justify-between items-center text-xs font-medium">
                                                <span className="text-slate-300">Intimitäts-Level (Spice): {spiceLevel}/5</span>
                                                <span className="text-primary font-semibold">
                                                    {spiceLevel === 1 ? 'Clean' : spiceLevel === 2 ? 'Mild' : spiceLevel === 3 ? 'Moderat' : spiceLevel === 4 ? 'Steamy' : 'Explicit'}
                                                </span>
                                            </div>
                                            <input 
                                                type="range" 
                                                min="1" 
                                                max="5" 
                                                value={spiceLevel} 
                                                onChange={(e) => setSpiceLevel(parseInt(e.target.value))}
                                                className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-primary focus:outline-none"
                                            />
                                            <p className="text-[10px] text-text-muted italic leading-snug">
                                                {genreProfile.spice_descriptions?.[spiceLevel] || ''}
                                            </p>
                                        </div>
                                    )}
                                </div>
                            )}

                            <div className="flex justify-end gap-2 pt-2">
                                <button 
                                    type="button"
                                    onClick={() => setShowCreateModal(false)}
                                    className="px-5 py-2.5 rounded-xl text-sm font-medium hover:bg-slate-800 text-slate-400"
                                >
                                    Abbrechen
                                </button>
                                <button 
                                    type="submit"
                                    disabled={isSubmitting}
                                    className="btn-primary py-2.5 px-6 rounded-xl text-sm flex items-center gap-2"
                                >
                                    {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                                    Projekt anlegen
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

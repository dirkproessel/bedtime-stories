import React, { useState, useEffect, useMemo } from 'react';
import { useStore } from '../store/useStore';
import { 
    Plus, 
    BookOpen, 
    Trash2, 
    ArrowRight, 
    Loader2, 
    RefreshCw, 
    ArrowLeft, 
    Layers, 
    Sparkles, 
    ChevronRight,
    Search,
    Check,
    X
} from 'lucide-react';
import BookEditor from './BookEditor';
import SeriesWizard from './SeriesWizard';
import SeriesView from './SeriesView';
import { 
    createProBook, 
    deleteProBook, 
    fetchGenreProfile, 
    fetchStories, 
    createAnthologyBook, 
    type StoryMeta 
} from '../lib/api';
import toast from 'react-hot-toast';
import { AUTHORS, formatAuthorStyles } from '../lib/authors';
import { GENRES } from './StoryCreator';

export default function BookDashboard() {
    const { 
        user,
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
    const [createModalMode, setCreateModalMode] = useState<'novel' | 'anthology'>('novel');
    const [showSeriesWizard, setShowSeriesWizard] = useState(false);

    // Novel Mode State
    const [title, setTitle] = useState('');
    const [prompt, setPrompt] = useState('');
    const [genre, setGenre] = useState('Fantasy');
    const [selectedAuthors, setSelectedAuthors] = useState<string[]>(['adams']);
    const [language, setLanguage] = useState<'de' | 'en'>('de');
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Novel Genre-specific config
    const [genreProfile, setGenreProfile] = useState<any>(null);
    const [selectedTropes, setSelectedTropes] = useState<string[]>([]);
    const [pov, setPov] = useState<string>('');
    const [spiceLevel, setSpiceLevel] = useState<number>(3);

    // Anthology Mode State
    const [anthologyTitle, setAnthologyTitle] = useState('');
    const [anthologySubtitle, setAnthologySubtitle] = useState('');
    const [anthologyAuthor, setAnthologyAuthor] = useState('');
    const [anthologyGenre, setAnthologyGenre] = useState('Erotik');
    const [anthologyAuthors, setAnthologyAuthors] = useState<string[]>(['adams']);
    const [anthologyLanguage, setAnthologyLanguage] = useState<'de' | 'en'>('de');
    
    // Anthology Stories Picker State
    const [anthologyStories, setAnthologyStories] = useState<StoryMeta[]>([]);
    const [selectedStoryIds, setSelectedStoryIds] = useState<string[]>([]);
    const [storyMap, setStoryMap] = useState<Record<string, StoryMeta>>({});
    const [storySearch, setStorySearch] = useState('');
    const [storyGenreFilter, setStoryGenreFilter] = useState('all');
    const [storiesPage, setStoriesPage] = useState(1);
    const [storiesHasMore, setStoriesHasMore] = useState(false);
    const [isLoadingStories, setIsLoadingStories] = useState(false);
    const [availableGenres, setAvailableGenres] = useState<string[]>([]);

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

    // Load genre profile when novel genre or modal changes
    useEffect(() => {
        if (!showCreateModal || createModalMode !== 'novel') return;
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
    }, [genre, showCreateModal, createModalMode]);

    // Load stories for anthology when switching to anthology mode or changing filters
    useEffect(() => {
        if (!showCreateModal || createModalMode !== 'anthology') return;

        if (user?.username && !anthologyAuthor) {
            setAnthologyAuthor(user.username);
        }

        const timer = setTimeout(() => {
            loadAnthologyStories(1, true);
        }, 200);

        return () => clearTimeout(timer);
    }, [showCreateModal, createModalMode, storySearch, storyGenreFilter]);

    const loadAnthologyStories = async (pageToLoad = 1, reset = false) => {
        setIsLoadingStories(true);
        try {
            const res = await fetchStories({
                page: pageToLoad,
                pageSize: 30,
                filter: 'my',
                search: storySearch.trim() || undefined,
                genre: storyGenreFilter !== 'all' ? [storyGenreFilter] : undefined
            });

            setStoryMap(prev => {
                const next = { ...prev };
                res.stories.forEach((s: StoryMeta) => { next[s.id] = s; });
                return next;
            });

            if (reset) {
                setAnthologyStories(res.stories);
            } else {
                setAnthologyStories(prev => {
                    const existingIds = new Set(prev.map(s => s.id));
                    const newOnes = res.stories.filter((s: StoryMeta) => !existingIds.has(s.id));
                    return [...prev, ...newOnes];
                });
            }

            setStoriesPage(pageToLoad);
            setStoriesHasMore(res.stories.length === 30 && (pageToLoad * 30 < res.total));
            if (res.available_genres && res.available_genres.length > 0) {
                setAvailableGenres(res.available_genres);
            }
        } catch (err: any) {
            console.error('Failed to load stories:', err);
        } finally {
            setIsLoadingStories(false);
        }
    };

    const toggleStorySelection = (story: StoryMeta) => {
        setStoryMap(prev => ({ ...prev, [story.id]: story }));
        setSelectedStoryIds(prev => {
            const isAlreadySelected = prev.includes(story.id);
            const next = isAlreadySelected 
                ? prev.filter(id => id !== story.id)
                : [...prev, story.id];

            // Auto update title if not customized
            if (!anthologyTitle.trim() || anthologyTitle.endsWith('-Geschichten') || anthologyTitle.includes('Sammelband')) {
                const g = story.genre || anthologyGenre || 'Kurzgeschichten';
                setAnthologyTitle(`${next.length} ${g}-Geschichten`);
            }
            return next;
        });
    };

    // Calculate anthology stats
    const selectedStoryList = useMemo(() => {
        return selectedStoryIds.map(id => storyMap[id]).filter(Boolean);
    }, [selectedStoryIds, storyMap]);

    const totalEstimatedWords = useMemo(() => {
        return selectedStoryList.reduce((acc, s) => {
            const w = s.duration_seconds ? Math.round((s.duration_seconds / 60) * 160) : 1500;
            return acc + w;
        }, 0);
    }, [selectedStoryList]);

    const totalEstimatedPages = Math.max(1, Math.round(totalEstimatedWords / 250));

    // Handle Novel Creation
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

    // Handle Anthology Creation
    const handleCreateAnthology = async (e: React.FormEvent) => {
        e.preventDefault();
        if (selectedStoryIds.length === 0) {
            toast.error('Bitte wähle mindestens eine Geschichte für den Sammelband aus.');
            return;
        }

        const finalTitle = anthologyTitle.trim() || `${selectedStoryIds.length} ${anthologyGenre}-Geschichten`;
        const styleString = anthologyAuthors.length > 0 ? anthologyAuthors.join(',') : 'adams';

        setIsSubmitting(true);
        try {
            const newProject = await createAnthologyBook({
                title: finalTitle,
                subtitle: anthologySubtitle.trim() || undefined,
                author: anthologyAuthor.trim() || (user?.username || 'Dirk Proessel'),
                genre: anthologyGenre,
                style: styleString,
                language: anthologyLanguage,
                story_ids: selectedStoryIds,
                auto_generate_blurb: false
            });

            toast.success(`Sammelband "${newProject.title}" mit ${selectedStoryIds.length} Geschichten erfolgreich erstellt!`);
            setShowCreateModal(false);
            setSelectedStoryIds([]);
            setAnthologyTitle('');
            setAnthologySubtitle('');
            
            // Immediately open in BookEditor
            await loadProProjects();
            await loadProProjectDetail(newProject.id);
        } catch (err: any) {
            console.error(err);
            toast.error(err.message || 'Fehler beim Erstellen des Sammelbands');
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
                        onClick={() => {
                            setCreateModalMode('anthology');
                            setShowCreateModal(true);
                        }}
                        className="px-4 py-2.5 bg-gradient-to-r from-amber-600 to-primary hover:from-amber-500 hover:to-primary-hover text-white rounded-xl text-sm font-semibold shadow-lg shadow-amber-500/20 flex items-center gap-2 transition-all cursor-pointer"
                    >
                        <Layers className="w-4 h-4" />
                        + Kurzgeschichten-Sammelband
                    </button>

                    <button 
                        onClick={() => {
                            setCreateModalMode('novel');
                            setShowCreateModal(true);
                        }}
                        className="btn-primary py-2.5 px-4 text-sm flex items-center gap-2 rounded-xl cursor-pointer"
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
                <div>
                    {proProjects.length === 0 ? (
                        <div className="text-center py-20 bg-surface/40 border border-slate-800 rounded-3xl space-y-4">
                            <BookOpen className="w-12 h-12 text-slate-600 mx-auto" />
                            <div>
                                <h3 className="text-white font-medium">Noch keine Buchprojekte vorhanden</h3>
                                <p className="text-xs text-text-muted mt-1">
                                    Erstelle deinen ersten Roman mit der neuen KI-Buch-Pipeline oder fasse Kurzgeschichten zusammen!
                                </p>
                            </div>
                            <div className="flex justify-center gap-3">
                                <button 
                                    onClick={() => {
                                        setCreateModalMode('anthology');
                                        setShowCreateModal(true);
                                    }}
                                    className="px-5 py-2.5 bg-gradient-to-r from-amber-600 to-primary text-white rounded-xl text-sm font-semibold inline-flex items-center gap-2 shadow-lg shadow-amber-500/20"
                                >
                                    <Layers className="w-4 h-4" />
                                    Sammelband erstellen
                                </button>
                                <button 
                                    onClick={() => {
                                        setCreateModalMode('novel');
                                        setShowCreateModal(true);
                                    }}
                                    className="btn-primary py-2.5 px-5 text-sm inline-flex items-center gap-2 rounded-xl"
                                >
                                    <Plus className="w-4 h-4" />
                                    Neuen Roman schreiben
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {proProjects.map(project => (
                                <div 
                                    key={project.id}
                                    onClick={() => handleOpenProject(project.id)}
                                    className="bg-surface border border-slate-800 rounded-3xl p-6 hover:border-primary/50 transition-all cursor-pointer group flex flex-col justify-between space-y-4 relative overflow-hidden"
                                >
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <span className="text-[11px] font-bold uppercase tracking-wider text-primary bg-primary/10 px-3 py-1 rounded-full border border-primary/20">
                                                    {project.genre} • {project.language === 'en' ? '🇬🇧 EN' : '🇩🇪 DE'}
                                                </span>
                                                {project.is_anthology && (
                                                    <span className="text-[10px] font-bold uppercase tracking-wider bg-amber-500/15 text-amber-300 border border-amber-500/30 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                                                        <Layers className="w-3 h-3" />
                                                        Sammelband
                                                    </span>
                                                )}
                                                {project.series_id && (
                                                    <span className="text-[10px] font-bold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full border border-indigo-500/30">
                                                        {project.series_subtitle || `Band ${project.series_order || 1}`}
                                                    </span>
                                                )}
                                            </div>
                                            <button 
                                                onClick={(e) => handleDeleteProject(project.id, e)}
                                                className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                                                title="Projekt löschen"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>

                                        <div>
                                            <h3 className="text-lg font-bold text-white group-hover:text-primary transition-colors line-clamp-1">
                                                {project.title}
                                            </h3>
                                            <p className="text-xs text-text-muted line-clamp-2 mt-1">
                                                {project.prompt}
                                            </p>
                                        </div>

                                        <div className="flex items-center gap-3 text-xs text-slate-400 pt-1">
                                            <span>{(project.chapters || []).length} Kapitel</span>
                                            <span>•</span>
                                            <span className="truncate">{formatAuthorStyles(project.style)}</span>
                                        </div>
                                    </div>

                                    <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
                                        <span className={`text-[11px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-lg ${
                                            project.status === 'completed' ? 'bg-primary/20 text-primary border border-primary/30' :
                                            project.status === 'generating' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30 animate-pulse' :
                                            project.status === 'proofreading' ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 animate-pulse' :
                                            'bg-slate-800 text-slate-400'
                                        }`}>
                                            {project.status === 'generating' ? 'Generiert...' : 
                                             project.status === 'proofreading' ? 'Lektorat...' :
                                             project.status === 'completed' ? 'Fertiggestellt' : 'Entwurf'}
                                        </span>

                                        <div className="flex items-center gap-1 text-xs text-primary font-semibold group-hover:translate-x-1 transition-transform">
                                            <span>Öffnen</span>
                                            <ArrowRight className="w-3.5 h-3.5" />
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Series Wizard Modal */}
            <SeriesWizard 
                isOpen={showSeriesWizard}
                onClose={() => setShowSeriesWizard(false)}
                onSuccess={(newSeries) => {
                    setCurrentProSeries(newSeries);
                }}
            />

            {/* Unified Create Project Modal (Roman vs. Sammelband) */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-background/85 backdrop-blur-md z-[1000] flex items-center justify-center p-4">
                    <div className={`bg-surface border border-slate-800 w-full rounded-3xl p-6 shadow-2xl relative space-y-5 transition-all max-h-[92vh] flex flex-col ${
                        createModalMode === 'anthology' ? 'max-w-3xl' : 'max-w-xl'
                    }`}>
                        {/* Modal Header & Mode Switcher Tabs */}
                        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                            <div className="flex items-center gap-2 bg-slate-900/80 p-1 rounded-2xl border border-slate-800">
                                <button
                                    type="button"
                                    onClick={() => setCreateModalMode('novel')}
                                    className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition-all ${
                                        createModalMode === 'novel'
                                            ? 'bg-primary text-white shadow-md'
                                            : 'text-slate-400 hover:text-white'
                                    }`}
                                >
                                    <BookOpen className="w-3.5 h-3.5" />
                                    Neuer Roman
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setCreateModalMode('anthology')}
                                    className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition-all ${
                                        createModalMode === 'anthology'
                                            ? 'bg-gradient-to-r from-amber-600 to-primary text-white shadow-md'
                                            : 'text-slate-400 hover:text-white'
                                    }`}
                                >
                                    <Layers className="w-3.5 h-3.5" />
                                    Kurzgeschichten-Sammelband
                                </button>
                            </div>

                            <button
                                type="button"
                                onClick={() => setShowCreateModal(false)}
                                className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* MODE 1: NOVEL FORM */}
                        {createModalMode === 'novel' && (
                            <form onSubmit={handleCreateProject} className="space-y-4 overflow-y-auto pr-1">
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
                                        rows={3}
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
                                                    Aktive Tropes (wähle narrative Elemente)
                                                </label>
                                                <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto pr-1">
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
                                            </div>
                                        )}
                                    </div>
                                )}

                                <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
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
                        )}

                        {/* MODE 2: ANTHOLOGY FORM */}
                        {createModalMode === 'anthology' && (
                            <form onSubmit={handleCreateAnthology} className="space-y-4 overflow-y-auto pr-1">
                                {/* Summary Badge of selected stories */}
                                <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-2xl flex items-center justify-between text-xs">
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold">
                                            {selectedStoryIds.length}
                                        </div>
                                        <div>
                                            <div className="font-bold text-white">
                                                {selectedStoryIds.length === 0 ? 'Wähle Geschichten für deinen Sammelband' : `${selectedStoryIds.length} Geschichten im Buch`}
                                            </div>
                                            <div className="text-text-muted text-[11px]">
                                                ~{totalEstimatedWords.toLocaleString()} Wörter • ca. {totalEstimatedPages} Buchseiten (Standard KDP-Format)
                                            </div>
                                        </div>
                                    </div>
                                    {selectedStoryIds.length > 0 && (
                                        <button
                                            type="button"
                                            onClick={() => setSelectedStoryIds([])}
                                            className="text-amber-400/80 hover:text-amber-300 text-[11px] underline"
                                        >
                                            Auswahl leeren
                                        </button>
                                    )}
                                </div>

                                {/* Step 1: Stories Picker */}
                                <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <label className="text-xs font-semibold text-slate-300">
                                            1. Kurzgeschichten auswählen ({selectedStoryIds.length} markiert)
                                        </label>
                                        <span className="text-[10px] text-slate-400">Durchsuche deine 500+ Geschichten</span>
                                    </div>

                                    {/* Search & Genre Filters */}
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                        <div className="relative">
                                            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                                            <input
                                                type="text"
                                                value={storySearch}
                                                onChange={(e) => setStorySearch(e.target.value)}
                                                placeholder="Titel oder Text suchen..."
                                                className="w-full pl-9 pr-3 py-1.5 bg-background border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-primary"
                                            />
                                        </div>

                                        <select
                                            value={storyGenreFilter}
                                            onChange={(e) => setStoryGenreFilter(e.target.value)}
                                            className="w-full px-3 py-1.5 bg-background border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-primary"
                                        >
                                            <option value="all">Alle Genres</option>
                                            {availableGenres.map(g => (
                                                <option key={g} value={g}>{g}</option>
                                            ))}
                                        </select>
                                    </div>

                                    {/* Stories List (compact scrollable) */}
                                    <div className="max-h-52 overflow-y-auto bg-background/90 border border-slate-800 rounded-2xl p-2 space-y-1.5 no-scrollbar">
                                        {isLoadingStories && anthologyStories.length === 0 ? (
                                            <div className="py-8 flex items-center justify-center gap-2 text-slate-400 text-xs">
                                                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                                                Lade Kurzgeschichten...
                                            </div>
                                        ) : anthologyStories.length === 0 ? (
                                            <div className="py-8 text-center text-slate-500 text-xs">
                                                Keine Geschichten mit diesen Filtern gefunden.
                                            </div>
                                        ) : (
                                            anthologyStories.map((story) => {
                                                const isSelected = selectedStoryIds.includes(story.id);
                                                return (
                                                    <div
                                                        key={story.id}
                                                        onClick={() => toggleStorySelection(story)}
                                                        className={`p-2.5 rounded-xl border text-xs cursor-pointer flex items-center justify-between gap-3 transition-all ${
                                                            isSelected
                                                                ? 'bg-amber-500/15 border-amber-500 text-white font-medium shadow-sm'
                                                                : 'border-slate-800/80 bg-slate-900/30 text-slate-300 hover:border-slate-700 hover:bg-slate-800/40'
                                                        }`}
                                                    >
                                                        <div className="flex items-center gap-2.5 min-w-0">
                                                            <div className={`w-4 h-4 rounded-md flex items-center justify-center border transition-all ${
                                                                isSelected 
                                                                    ? 'bg-amber-500 border-amber-400 text-black' 
                                                                    : 'border-slate-700 bg-slate-950'
                                                            }`}>
                                                                {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                                                            </div>
                                                            <div className="min-w-0">
                                                                <div className="font-semibold text-slate-200 truncate">{story.title}</div>
                                                                <div className="text-[10px] text-text-muted truncate mt-0.5">
                                                                    {story.genre || 'Kurzgeschichte'} {story.created_at ? `• ${new Date(story.created_at).toLocaleDateString('de-DE')}` : ''}
                                                                </div>
                                                            </div>
                                                        </div>

                                                        <div className="shrink-0 flex items-center gap-2">
                                                            {story.duration_seconds && (
                                                                <span className="text-[10px] bg-slate-950 px-2 py-0.5 rounded-full text-slate-400 border border-slate-800">
                                                                    ~{Math.round(story.duration_seconds / 60)} Min
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                );
                                            })
                                        )}

                                        {storiesHasMore && (
                                            <button
                                                type="button"
                                                onClick={() => loadAnthologyStories(storiesPage + 1, false)}
                                                disabled={isLoadingStories}
                                                className="w-full py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-semibold rounded-xl border border-slate-800 flex items-center justify-center gap-2 transition-all mt-1"
                                            >
                                                {isLoadingStories && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                                                Weitere Geschichten laden...
                                            </button>
                                        )}
                                    </div>
                                </div>

                                {/* Step 2: Book Details */}
                                <div className="space-y-3 pt-2 border-t border-slate-800">
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                        <div className="space-y-1">
                                            <label className="text-xs font-medium text-slate-300">Buchtitel</label>
                                            <input 
                                                type="text" 
                                                value={anthologyTitle}
                                                onChange={(e) => setAnthologyTitle(e.target.value)}
                                                className="w-full bg-background border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
                                                placeholder="z. B. 10 Sinnliche Nächte: Erotischer Sammelband"
                                            />
                                        </div>

                                        <div className="space-y-1">
                                            <label className="text-xs font-medium text-slate-300">Untertitel (optional)</label>
                                            <input 
                                                type="text" 
                                                value={anthologySubtitle}
                                                onChange={(e) => setAnthologySubtitle(e.target.value)}
                                                className="w-full bg-background border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
                                                placeholder="z. B. Ein exklusiver Kurzgeschichten-Band"
                                            />
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                        <div className="space-y-1">
                                            <label className="text-xs font-medium text-slate-300">Autor / Pseudonym</label>
                                            <input 
                                                type="text" 
                                                value={anthologyAuthor}
                                                onChange={(e) => setAnthologyAuthor(e.target.value)}
                                                className="w-full bg-background border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
                                                placeholder="Dein Autorenname"
                                            />
                                        </div>

                                        <div className="space-y-1">
                                            <label className="text-xs font-medium text-slate-300">Hauptgenre</label>
                                            <select 
                                                value={anthologyGenre}
                                                onChange={(e) => setAnthologyGenre(e.target.value)}
                                                className="w-full bg-background border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
                                            >
                                                {GENRES.map(g => (
                                                    <option key={g.value} value={g.value}>{g.label}</option>
                                                ))}
                                            </select>
                                        </div>

                                        <div className="space-y-1">
                                            <label className="text-xs font-medium text-slate-300">Sprache</label>
                                            <div className="grid grid-cols-2 gap-1.5">
                                                <button
                                                    type="button"
                                                    onClick={() => setAnthologyLanguage('de')}
                                                    className={`py-1.5 px-2 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1 transition-all ${
                                                        anthologyLanguage === 'de'
                                                            ? 'bg-amber-500/20 border-amber-500 text-amber-300'
                                                            : 'bg-background border-slate-800 text-slate-400'
                                                    }`}
                                                >
                                                    🇩🇪 DE
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => setAnthologyLanguage('en')}
                                                    className={`py-1.5 px-2 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1 transition-all ${
                                                        anthologyLanguage === 'en'
                                                            ? 'bg-amber-500/20 border-amber-500 text-amber-300'
                                                            : 'bg-background border-slate-800 text-slate-400'
                                                    }`}
                                                >
                                                    🇬🇧 EN
                                                </button>
                                            </div>
                                        </div>
                                    </div>

                                    {/* 3-Author Style Mixer */}
                                    <div className="space-y-1">
                                        <div className="flex justify-between items-center">
                                            <label className="text-xs font-medium text-slate-300">Stil-Bibel & Cover-Inspiration (Mixe bis zu 3 Autoren)</label>
                                            <span className="text-[10px] text-amber-400 font-bold">{anthologyAuthors.length}/3 gewählt</span>
                                        </div>
                                        <div className="max-h-28 overflow-y-auto bg-background border border-slate-800 rounded-xl p-1.5 space-y-1 no-scrollbar">
                                            {AUTHORS.map(a => {
                                                const isSelected = anthologyAuthors.includes(a.id);
                                                const authorIndex = anthologyAuthors.indexOf(a.id);
                                                return (
                                                    <div 
                                                        key={a.id}
                                                        onClick={() => {
                                                            if (isSelected) {
                                                                setAnthologyAuthors(anthologyAuthors.filter(id => id !== a.id));
                                                            } else if (anthologyAuthors.length < 3) {
                                                                setAnthologyAuthors([...anthologyAuthors, a.id]);
                                                            } else {
                                                                toast('Maximal 3 Autoren können kombiniert werden', { icon: 'ℹ️' });
                                                            }
                                                        }}
                                                        className={`p-1.5 rounded-lg border text-xs cursor-pointer flex items-center justify-between transition-all ${
                                                            isSelected 
                                                                ? 'bg-amber-500/15 border-amber-500 text-white font-medium shadow-sm' 
                                                                : 'border-slate-800/80 bg-slate-900/40 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                                                        }`}
                                                    >
                                                        <div className="min-w-0">
                                                            <div className="text-[11px] font-semibold truncate">{a.name}</div>
                                                            <div className="text-[9px] text-slate-500 truncate">{a.desc}</div>
                                                        </div>
                                                        {isSelected && (
                                                            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-500/30 text-amber-300 border border-amber-500/40 shrink-0">
                                                                {authorIndex === 0 ? '1. Wortwahl' : authorIndex === 1 ? '2. Atmosphäre' : '3. Erzählweise'}
                                                            </span>
                                                        )}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                </div>

                                <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                                    <button 
                                        type="button"
                                        onClick={() => setShowCreateModal(false)}
                                        className="px-5 py-2.5 rounded-xl text-sm font-medium hover:bg-slate-800 text-slate-400"
                                    >
                                        Abbrechen
                                    </button>
                                    <button 
                                        type="submit"
                                        disabled={isSubmitting || selectedStoryIds.length === 0}
                                        className="px-6 py-2.5 bg-gradient-to-r from-amber-600 to-primary hover:from-amber-500 hover:to-primary-hover text-white rounded-xl text-sm font-bold shadow-lg shadow-amber-500/20 flex items-center gap-2 transition-all disabled:opacity-50"
                                    >
                                        {isSubmitting ? (
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                        ) : (
                                            <Layers className="w-4 h-4" />
                                        )}
                                        Sammelband erstellen ({selectedStoryIds.length} Geschichten)
                                    </button>
                                </div>
                            </form>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

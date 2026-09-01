import React, { useState, useEffect } from 'react';
import { 
    ArrowLeft, 
    Plus, 
    BookOpen, 
    Trash2, 
    Sparkles, 
    Layers, 
    Save, 
    Edit2, 
    ChevronRight, 
    Users, 
    Globe, 
    Image as ImageIcon, 
    Loader2, 
    X, 
    Compass, 
    RefreshCw, 
    Check
} from 'lucide-react';
import { useStore } from '../store/useStore';
import { 
    type BookSeriesDetail, 
    type SequelPitch, 
    updateProSeries, 
    suggestProSequel, 
    createProSequel, 
    syncProSeriesBible,
    getProCoverUrl,
    deleteProBook
} from '../lib/api';
import toast from 'react-hot-toast';

interface SeriesViewProps {
    series: BookSeriesDetail;
    onBack: () => void;
}

type SeriesTab = 'volumes' | 'bible' | 'cover';

export default function SeriesView({ series: initialSeries, onBack }: SeriesViewProps) {
    const { 
        loadProSeriesDetail, 
        loadProProjectDetail, 
        deleteProSeries, 
        loadProProjects 
    } = useStore();

    const [series, setSeries] = useState<BookSeriesDetail>(initialSeries);
    const [activeTab, setActiveTab] = useState<SeriesTab>('volumes');

    // Bible Editing State
    const [isEditingBible, setIsEditingBible] = useState(false);
    const [worldLore, setWorldLore] = useState(series.world_lore || '');
    const [seriesArc, setSeriesArc] = useState(series.series_arc || '');
    const [styleBible, setStyleBible] = useState(series.style_bible || '');
    const [charactersJson, setCharactersJson] = useState(series.characters_bible || '[]');
    const [coverStylePrompt, setCoverStylePrompt] = useState(series.cover_style_prompt || '');
    const [isSavingBible, setIsSavingBible] = useState(false);

    // Sequel Modal State
    const [showSequelModal, setShowSequelModal] = useState(false);
    const [isLoadingPitches, setIsLoadingPitches] = useState(false);
    const [pitches, setPitches] = useState<SequelPitch[]>([]);
    const [selectedPitchIndex, setSelectedPitchIndex] = useState<number | null>(null);
    const [sequelTitle, setSequelTitle] = useState('');
    const [sequelSubtitle, setSequelSubtitle] = useState('');
    const [sequelPrompt, setSequelPrompt] = useState('');
    const [autoEvolveChars, setAutoEvolveChars] = useState(true);
    const [isCreatingSequel, setIsCreatingSequel] = useState(false);

    // Sync state
    const [isSyncingBible, setIsSyncingBible] = useState(false);

    useEffect(() => {
        setSeries(initialSeries);
        setWorldLore(initialSeries.world_lore || '');
        setSeriesArc(initialSeries.series_arc || '');
        setStyleBible(initialSeries.style_bible || '');
        setCharactersJson(initialSeries.characters_bible || '[]');
        setCoverStylePrompt(initialSeries.cover_style_prompt || '');
    }, [initialSeries]);

    const refreshSeries = async () => {
        try {
            await loadProSeriesDetail(series.id);
        } catch (e: any) {
            toast.error('Fehler beim Aktualisieren der Serie: ' + e.message);
        }
    };

    // Save Bible Changes
    const handleSaveBible = async () => {
        setIsSavingBible(true);
        try {
            const updated = await updateProSeries(series.id, {
                world_lore: worldLore,
                series_arc: seriesArc,
                style_bible: styleBible,
                characters_bible: charactersJson,
                cover_style_prompt: coverStylePrompt
            });
            setSeries(prev => ({ ...prev, ...updated }));
            setIsEditingBible(false);
            toast.success('Serien-Bibel gespeichert!');
        } catch (e: any) {
            toast.error('Fehler beim Speichern: ' + e.message);
        } finally {
            setIsSavingBible(false);
        }
    };

    // Open Sequel Modal & load pitches
    const handleOpenSequelModal = async () => {
        const isEn = series.language === 'en';
        setShowSequelModal(true);
        setIsLoadingPitches(true);
        setPitches([]);
        setSelectedPitchIndex(null);
        setSequelTitle('');
        setSequelSubtitle(`${isEn ? 'Volume' : 'Band'} ${(series.books?.length || 0) + 1}`);
        setSequelPrompt('');

        try {
            const res = await suggestProSequel(series.id);
            setPitches(res.pitches || []);
            if (res.pitches && res.pitches.length > 0) {
                const first = res.pitches[0];
                setSelectedPitchIndex(0);
                setSequelTitle(first.title);
                setSequelSubtitle(first.subtitle);
                setSequelPrompt(first.pitch);
            }
        } catch (e: any) {
            toast.error('Konnte keine Pitches laden: ' + e.message);
        } finally {
            setIsLoadingPitches(false);
        }
    };

    const handleSelectPitch = (index: number) => {
        setSelectedPitchIndex(index);
        const p = pitches[index];
        if (p) {
            setSequelTitle(p.title);
            setSequelSubtitle(p.subtitle);
            setSequelPrompt(p.pitch);
        }
    };

    const handleCreateSequelSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!sequelTitle.trim() || !sequelPrompt.trim()) {
            toast.error('Bitte Titel und Handlungs-Prämisse angeben');
            return;
        }

        setIsCreatingSequel(true);
        try {
            const newBook = await createProSequel(series.id, {
                title: sequelTitle.trim(),
                subtitle: sequelSubtitle.trim(),
                prompt: sequelPrompt.trim(),
                auto_evolve_characters: autoEvolveChars
            });

            toast.success(`Band ${(series.books?.length || 0) + 1} erfolgreich erstellt!`);
            setShowSequelModal(false);
            await refreshSeries();
            await loadProProjects();

            // Directly open new volume in editor
            await loadProProjectDetail(newBook.id);
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Erstellen der Fortsetzung');
        } finally {
            setIsCreatingSequel(false);
        }
    };

    const handleDeleteSeries = async () => {
        if (!window.confirm(`Möchtest du die Serie "${series.title}" wirklich löschen? Die enthaltenen Bücher bleiben als Einzelbände erhalten.`)) return;
        try {
            await deleteProSeries(series.id);
            toast.success('Serie gelöscht');
            onBack();
        } catch (e: any) {
            toast.error('Fehler beim Löschen: ' + e.message);
        }
    };

    const handleDeleteBook = async (bookId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!window.confirm('Möchtest du diesen Band wirklich unwiderruflich löschen?')) return;
        try {
            await deleteProBook(bookId);
            toast.success('Band gelöscht');
            await refreshSeries();
            await loadProProjects();
        } catch (e: any) {
            toast.error('Fehler beim Löschen: ' + e.message);
        }
    };

    const handleSyncBibleFromBook = async (bookId: string) => {
        setIsSyncingBible(true);
        try {
            const res = await syncProSeriesBible(series.id, bookId);
            toast.success(res.message || 'Serien-Bibel synchronisiert');
            await refreshSeries();
        } catch (e: any) {
            toast.error('Fehler beim Synchronisieren: ' + e.message);
        } finally {
            setIsSyncingBible(false);
        }
    };

    // Parse characters for display
    let parsedCharacters: any[] = [];
    try {
        if (charactersJson) {
            parsedCharacters = JSON.parse(charactersJson);
            if (!Array.isArray(parsedCharacters)) parsedCharacters = [];
        }
    } catch {
        parsedCharacters = [];
    }

    const nextVolumeNum = (series.books?.length || 0) + 1;
    const isCompleted = series.planned_volumes && series.books && series.books.length >= series.planned_volumes;

    return (
        <div className="space-y-6">
            
            {/* Header Banner */}
            <div className="bg-gradient-to-br from-indigo-950/60 via-surface to-surface border border-indigo-500/20 rounded-3xl p-6 sm:p-8 shadow-xl relative overflow-hidden">
                <div className="absolute -top-24 -right-24 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
                
                <div className="relative space-y-6">
                    {/* Top action row */}
                    <div className="flex items-center justify-between">
                        <button 
                            onClick={onBack}
                            className="inline-flex items-center gap-2 px-3.5 py-2 bg-surface/80 hover:bg-slate-800 text-slate-300 hover:text-white rounded-xl text-xs font-semibold transition-colors border border-slate-700/60"
                        >
                            <ArrowLeft className="w-4 h-4" />
                            Zurück zur Übersicht
                        </button>

                        <div className="flex items-center gap-2">
                            <button 
                                onClick={refreshSeries}
                                className="p-2.5 bg-surface/80 hover:bg-slate-800 text-slate-300 hover:text-white rounded-xl transition-colors border border-slate-700/60"
                                title="Aktualisieren"
                            >
                                <RefreshCw className="w-4 h-4" />
                            </button>
                            <button 
                                onClick={handleDeleteSeries}
                                className="p-2.5 bg-surface/80 hover:bg-rose-950/40 text-slate-400 hover:text-rose-400 rounded-xl transition-colors border border-slate-700/60"
                                title="Serie auflösen"
                            >
                                <Trash2 className="w-4 h-4" />
                            </button>
                        </div>
                    </div>

                    {/* Series Title, Badges & Premise */}
                    <div className="space-y-3">
                        <div className="flex flex-wrap items-center gap-2.5">
                            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1.5">
                                <Layers className="w-3.5 h-3.5" />
                                Buch-Serie
                            </span>
                            <span className="px-3 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
                                {series.language === 'en' ? '🇬🇧 EN' : '🇩🇪 DE'}
                            </span>
                            <span className="px-3 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
                                {series.genre}
                            </span>
                            <span className="px-3 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
                                {series.books?.length || 0} {series.planned_volumes ? `von ${series.planned_volumes} Bänden` : 'Bände'}
                            </span>
                            {isCompleted && (
                                <span className="px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                    Vollständig abgeschlossen
                                </span>
                            )}
                        </div>

                        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
                            {series.title}
                        </h1>

                        <p className="text-sm text-slate-300 max-w-3xl leading-relaxed">
                            {series.description}
                        </p>
                    </div>

                    {/* Navigation Tabs */}
                    <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-800/80">
                        <button
                            onClick={() => setActiveTab('volumes')}
                            className={`px-4 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 transition-all ${
                                activeTab === 'volumes'
                                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/25'
                                    : 'bg-surface/60 hover:bg-slate-800 text-slate-300 border border-slate-800'
                            }`}
                        >
                            <BookOpen className="w-4 h-4" />
                            Bände & Chronologie ({series.books?.length || 0})
                        </button>

                        <button
                            onClick={() => setActiveTab('bible')}
                            className={`px-4 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 transition-all ${
                                activeTab === 'bible'
                                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/25'
                                    : 'bg-surface/60 hover:bg-slate-800 text-slate-300 border border-slate-800'
                            }`}
                        >
                            <Users className="w-4 h-4" />
                            Master-Serien-Bibel & Lore
                        </button>

                        <button
                            onClick={() => setActiveTab('cover')}
                            className={`px-4 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 transition-all ${
                                activeTab === 'cover'
                                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/25'
                                    : 'bg-surface/60 hover:bg-slate-800 text-slate-300 border border-slate-800'
                            }`}
                        >
                            <ImageIcon className="w-4 h-4" />
                            Cover-Design-System
                        </button>
                    </div>
                </div>
            </div>

            {/* TAB 1: VOLUMES */}
            {activeTab === 'volumes' && (
                <div className="space-y-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <h2 className="text-xl font-bold text-white">Chronologie der Reihe</h2>
                            <p className="text-xs text-text-muted mt-0.5">Alle Bände dieser Serie in ihrer Veröffentlichungsreihenfolge.</p>
                        </div>

                        <button
                            onClick={handleOpenSequelModal}
                            className="btn-primary py-2.5 px-5 text-sm flex items-center gap-2 rounded-xl shadow-lg shadow-indigo-500/20"
                        >
                            <Sparkles className="w-4 h-4" />
                            + Fortsetzung (Band {nextVolumeNum}) planen
                        </button>
                    </div>

                    {/* Book list */}
                    {(!series.books || series.books.length === 0) ? (
                        <div className="text-center py-16 bg-surface/40 border border-slate-800 rounded-3xl space-y-4">
                            <BookOpen className="w-12 h-12 text-slate-600 mx-auto" />
                            <div>
                                <h3 className="text-white font-semibold">Noch keine Bände in dieser Serie</h3>
                                <p className="text-xs text-text-muted mt-1">Starte jetzt mit Band 1 oder plane den ersten Band.</p>
                            </div>
                            <button
                                onClick={handleOpenSequelModal}
                                className="btn-primary py-2 px-4 text-xs inline-flex items-center gap-2 rounded-xl"
                            >
                                <Plus className="w-4 h-4" />
                                Band 1 anlegen
                            </button>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                            {series.books.map((book, idx) => {
                                const volNum = book.series_order || idx + 1;
                                const coverUrl = book.cover_image_url ? getProCoverUrl(book.id) : null;
                                
                                return (
                                    <div 
                                        key={book.id}
                                        onClick={() => loadProProjectDetail(book.id)}
                                        className="group bg-surface/70 hover:bg-surface border border-slate-800 hover:border-indigo-500/40 rounded-3xl p-5 transition-all duration-200 cursor-pointer shadow-lg hover:shadow-indigo-500/10 flex flex-col justify-between space-y-4"
                                    >
                                        <div className="space-y-4">
                                            {/* Cover & Volume Header */}
                                            <div className="flex gap-4">
                                                <div className="w-20 h-28 rounded-xl bg-slate-950 border border-slate-800 overflow-hidden flex-shrink-0 relative group-hover:scale-105 transition-transform">
                                                    {coverUrl ? (
                                                        <img 
                                                            src={coverUrl} 
                                                            alt={book.title}
                                                            className="w-full h-full object-cover" 
                                                        />
                                                    ) : (
                                                        <div className="w-full h-full flex flex-col items-center justify-center p-2 text-center text-slate-600">
                                                            <BookOpen className="w-6 h-6 mb-1" />
                                                            <span className="text-[10px]">Kein Cover</span>
                                                        </div>
                                                    )}
                                                    <div className="absolute top-1 left-1 px-1.5 py-0.5 rounded bg-black/80 backdrop-blur-md text-[10px] font-bold text-white">
                                                        B{volNum}
                                                    </div>
                                                </div>

                                                <div className="flex-1 min-w-0 space-y-1">
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider">
                                                            {series?.language === 'en' ? `Volume ${volNum}` : `Band ${volNum}`}
                                                        </span>
                                                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                                                            book.status === 'completed' ? 'bg-emerald-500/20 text-emerald-300' :
                                                            book.status === 'generating' ? 'bg-amber-500/20 text-amber-300 animate-pulse' :
                                                            'bg-slate-800 text-slate-400'
                                                        }`}>
                                                            {book.status === 'completed' ? 'Fertig' : book.status === 'generating' ? 'Schreibt...' : 'Entwurf'}
                                                        </span>
                                                    </div>
                                                    <h3 className="text-base font-bold text-white group-hover:text-indigo-300 transition-colors line-clamp-2">
                                                        {book.title}
                                                    </h3>
                                                    <p className="text-xs text-text-muted line-clamp-2">
                                                        {book.prompt}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Actions */}
                                        <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-text-muted">
                                            <span className="font-medium">
                                                {book.chapters?.length ? `${book.chapters.length} Kapitel` : 'Im Aufbau'}
                                            </span>
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleSyncBibleFromBook(book.id);
                                                    }}
                                                    disabled={isSyncingBible}
                                                    className="p-1.5 text-slate-400 hover:text-indigo-300 hover:bg-slate-800 rounded-lg transition-colors"
                                                    title="Charaktere dieses Bandes in die Serien-Bibel übernehmen"
                                                >
                                                    <Users className="w-3.5 h-3.5" />
                                                </button>
                                                <button
                                                    onClick={(e) => handleDeleteBook(book.id, e)}
                                                    className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
                                                    title="Band löschen"
                                                >
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                </button>
                                                <span className="flex items-center text-indigo-400 font-semibold group-hover:translate-x-0.5 transition-transform">
                                                    Öffnen <ChevronRight className="w-4 h-4 ml-0.5" />
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}

            {/* TAB 2: MASTER SERIES BIBLE */}
            {activeTab === 'bible' && (
                <div className="space-y-6">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                        <div>
                            <h2 className="text-xl font-bold text-white flex items-center gap-2">
                                <Users className="w-5 h-5 text-indigo-400" />
                                Master-Serien-Bibel
                            </h2>
                            <p className="text-xs text-text-muted mt-0.5">
                                Diese Daten (Lore, Stamm-Charaktere, Story-Arc) gelten für alle Bände der Serie und werden an neue Fortsetzungen vererbt.
                            </p>
                        </div>

                        <div className="flex gap-2">
                            {isEditingBible ? (
                                <>
                                    <button
                                        onClick={() => setIsEditingBible(false)}
                                        className="px-4 py-2 bg-surface hover:bg-slate-800 text-slate-300 rounded-xl text-xs font-semibold border border-slate-700 transition-colors"
                                    >
                                        Abbrechen
                                    </button>
                                    <button
                                        onClick={handleSaveBible}
                                        disabled={isSavingBible}
                                        className="btn-primary px-5 py-2 text-xs font-semibold rounded-xl flex items-center gap-2"
                                    >
                                        {isSavingBible ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                        Änderungen speichern
                                    </button>
                                </>
                            ) : (
                                <button
                                    onClick={() => setIsEditingBible(true)}
                                    className="px-4 py-2 bg-surface hover:bg-slate-800 text-slate-300 hover:text-white rounded-xl text-xs font-semibold border border-slate-700 transition-colors flex items-center gap-2"
                                >
                                    <Edit2 className="w-3.5 h-3.5" />
                                    Bibel bearbeiten
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Master Characters Section */}
                    <div className="bg-surface/60 border border-slate-800 rounded-3xl p-6 space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-base font-bold text-white flex items-center gap-2">
                                <Users className="w-4 h-4 text-indigo-400" />
                                Stammbesetzung (Wiederkehrende Haupt- & Nebenfiguren)
                            </h3>
                            <span className="text-xs text-text-muted">
                                {parsedCharacters.length} Charaktere
                            </span>
                        </div>

                        {isEditingBible ? (
                            <div className="space-y-1.5">
                                <label className="text-xs text-slate-400">Charaktere (JSON-Format):</label>
                                <textarea
                                    value={charactersJson}
                                    onChange={(e) => setCharactersJson(e.target.value)}
                                    rows={8}
                                    className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 font-mono text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors"
                                />
                            </div>
                        ) : parsedCharacters.length > 0 ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {parsedCharacters.map((c, i) => (
                                    <div key={i} className="p-4 bg-slate-900/80 border border-slate-800 rounded-2xl space-y-2">
                                        <div className="flex items-center justify-between">
                                            <h4 className="text-sm font-bold text-white">{c.name}</h4>
                                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-medium">
                                                {c.role || 'Figur'}
                                            </span>
                                        </div>
                                        <p className="text-xs text-slate-300 leading-relaxed">{c.description}</p>
                                        {c.traits && Array.isArray(c.traits) && (
                                            <div className="flex flex-wrap gap-1.5 pt-1">
                                                {c.traits.map((t: string, ti: number) => (
                                                    <span key={ti} className="text-[10px] px-2 py-0.5 rounded-md bg-slate-800 text-slate-400">
                                                        {t}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-xs text-text-muted italic">Keine Stamm-Charaktere hinterlegt.</p>
                        )}
                    </div>

                    {/* World Lore Section */}
                    <div className="bg-surface/60 border border-slate-800 rounded-3xl p-6 space-y-4">
                        <h3 className="text-base font-bold text-white flex items-center gap-2">
                            <Globe className="w-4 h-4 text-indigo-400" />
                            Worldbuilding, Schauplätze & Universum
                        </h3>
                        {isEditingBible ? (
                            <textarea
                                value={worldLore}
                                onChange={(e) => setWorldLore(e.target.value)}
                                rows={6}
                                placeholder="Weltregeln, Geografie, Magiesystem/Technologie, Fraktionen, Zeitalter..."
                                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors resize-none leading-relaxed"
                            />
                        ) : (
                            <p className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
                                {worldLore || 'Keine World-Lore hinterlegt.'}
                            </p>
                        )}
                    </div>

                    {/* Series Arc Section */}
                    <div className="bg-surface/60 border border-slate-800 rounded-3xl p-6 space-y-4">
                        <h3 className="text-base font-bold text-white flex items-center gap-2">
                            <Compass className="w-4 h-4 text-indigo-400" />
                            Übergeordneter Serien-Handlungsbogen (Series Arc)
                        </h3>
                        {isEditingBible ? (
                            <textarea
                                value={seriesArc}
                                onChange={(e) => setSeriesArc(e.target.value)}
                                rows={4}
                                placeholder="Meilensteine der einzelnen Bände (Band 1: ..., Band 2: ..., Band 3: ...)"
                                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors resize-none leading-relaxed"
                            />
                        ) : (
                            <p className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
                                {seriesArc || 'Kein Serien-Handlungsbogen hinterlegt.'}
                            </p>
                        )}
                    </div>
                </div>
            )}

            {/* TAB 3: COVER DESIGN SYSTEM */}
            {activeTab === 'cover' && (
                <div className="space-y-6">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                        <div>
                            <h2 className="text-xl font-bold text-white flex items-center gap-2">
                                <ImageIcon className="w-5 h-5 text-indigo-400" />
                                Cover-Design-System der Serie
                            </h2>
                            <p className="text-xs text-text-muted mt-0.5">
                                Einheitliches typografisches Layout, Beleuchtung und Grafikstil für den perfekten Franchise-Look.
                            </p>
                        </div>

                        {isEditingBible ? (
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setIsEditingBible(false)}
                                    className="px-4 py-2 bg-surface hover:bg-slate-800 text-slate-300 rounded-xl text-xs font-semibold border border-slate-700 transition-colors"
                                >
                                    Abbrechen
                                </button>
                                <button
                                    onClick={handleSaveBible}
                                    disabled={isSavingBible}
                                    className="btn-primary px-5 py-2 text-xs font-semibold rounded-xl flex items-center gap-2"
                                >
                                    {isSavingBible ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                    Speichern
                                </button>
                            </div>
                        ) : (
                            <button
                                onClick={() => setIsEditingBible(true)}
                                className="px-4 py-2 bg-surface hover:bg-slate-800 text-slate-300 hover:text-white rounded-xl text-xs font-semibold border border-slate-700 transition-colors flex items-center gap-2"
                            >
                                <Edit2 className="w-3.5 h-3.5" />
                                Template bearbeiten
                            </button>
                        )}
                    </div>

                    {/* Template Prompt */}
                    <div className="bg-surface/60 border border-slate-800 rounded-3xl p-6 space-y-3">
                        <h3 className="text-sm font-bold text-white">Cover-Prompt-Template (Englisch)</h3>
                        {isEditingBible ? (
                            <textarea
                                value={coverStylePrompt}
                                onChange={(e) => setCoverStylePrompt(e.target.value)}
                                rows={4}
                                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 font-mono text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors resize-none leading-relaxed"
                            />
                        ) : (
                            <p className="font-mono text-xs text-indigo-300/90 bg-slate-950 p-4 rounded-xl border border-slate-800 whitespace-pre-wrap leading-relaxed">
                                {coverStylePrompt || 'Kein Cover-Style-Template hinterlegt.'}
                            </p>
                        )}
                    </div>

                    {/* Visual Cover Gallery */}
                    <div className="bg-surface/60 border border-slate-800 rounded-3xl p-6 space-y-4">
                        <h3 className="text-sm font-bold text-white">Cover-Galerie der Serie (Stil-Vergleich)</h3>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                            {series.books?.map((b, i) => {
                                const url = b.cover_image_url ? getProCoverUrl(b.id) : null;
                                return (
                                    <div key={b.id} className="space-y-2 group">
                                        <div className="aspect-[2/3] rounded-2xl bg-slate-950 border border-slate-800 overflow-hidden relative shadow-lg group-hover:scale-105 transition-transform">
                                            {url ? (
                                                <img src={url} alt={b.title} className="w-full h-full object-cover" />
                                            ) : (
                                                <div className="w-full h-full flex flex-col items-center justify-center p-3 text-center text-slate-600">
                                                    <BookOpen className="w-8 h-8 mb-2" />
                                                    <span className="text-xs">Noch kein Cover</span>
                                                </div>
                                            )}
                                            <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-black/80 backdrop-blur-md text-xs font-bold text-white">
                                                Band {b.series_order || i + 1}
                                            </div>
                                        </div>
                                        <p className="text-xs font-semibold text-white truncate text-center">
                                            {b.title}
                                        </p>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            )}

            {/* SEQUEL WIZARD MODAL */}
            {showSequelModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md overflow-y-auto">
                    <div className="bg-slate-900 border border-indigo-500/30 rounded-3xl p-6 sm:p-8 max-w-2xl w-full shadow-2xl space-y-6 animate-in fade-in zoom-in-95 duration-200 my-8">
                        
                        {/* Header */}
                        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
                                    <Sparkles className="w-5 h-5" />
                                </div>
                                <div>
                                    <h3 className="text-xl font-bold text-white">
                                        Fortsetzung (Band {nextVolumeNum}) planen
                                    </h3>
                                    <p className="text-xs text-text-muted mt-0.5">
                                        Serie: {series.title}
                                    </p>
                                </div>
                            </div>
                            <button 
                                onClick={() => setShowSequelModal(false)}
                                disabled={isCreatingSequel}
                                className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition-colors disabled:opacity-50"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Pitches Section */}
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <label className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                                    <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                                    KI-Pitches für den nächsten Band
                                </label>
                                <button
                                    type="button"
                                    onClick={handleOpenSequelModal}
                                    disabled={isLoadingPitches}
                                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors"
                                >
                                    <RefreshCw className={`w-3 h-3 ${isLoadingPitches ? 'animate-spin' : ''}`} />
                                    Neu generieren
                                </button>
                            </div>

                            {isLoadingPitches ? (
                                <div className="py-8 text-center space-y-2 bg-surface/40 rounded-2xl border border-slate-800">
                                    <Loader2 className="w-6 h-6 animate-spin text-indigo-400 mx-auto" />
                                    <p className="text-xs text-slate-300">Analysiere Handlungsverlauf und erstelle Fortsetzungs-Optionen...</p>
                                </div>
                            ) : pitches.length > 0 ? (
                                <div className="grid grid-cols-1 gap-2.5 max-h-56 overflow-y-auto pr-1">
                                    {pitches.map((p, idx) => {
                                        const isSelected = selectedPitchIndex === idx;
                                        return (
                                            <div
                                                key={idx}
                                                onClick={() => handleSelectPitch(idx)}
                                                className={`p-3.5 rounded-2xl border transition-all cursor-pointer space-y-1.5 ${
                                                    isSelected 
                                                        ? 'bg-indigo-950/40 border-indigo-500 shadow-md shadow-indigo-500/10'
                                                        : 'bg-surface/50 hover:bg-surface border-slate-800'
                                                }`}
                                            >
                                                <div className="flex items-center justify-between">
                                                    <h4 className="text-xs font-bold text-white flex items-center gap-2">
                                                        {p.title}
                                                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300">
                                                            {p.tone}
                                                        </span>
                                                    </h4>
                                                    {isSelected && <Check className="w-4 h-4 text-indigo-400" />}
                                                </div>
                                                <p className="text-xs text-slate-300 leading-relaxed">{p.pitch}</p>
                                            </div>
                                        );
                                    })}
                                </div>
                            ) : null}
                        </div>

                        {/* Form */}
                        <form onSubmit={handleCreateSequelSubmit} className="space-y-4">
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                <div className="sm:col-span-2 space-y-1">
                                    <label className="text-xs font-semibold text-slate-300">Buchtitel für Band {nextVolumeNum} *</label>
                                    <input 
                                        type="text"
                                        value={sequelTitle}
                                        onChange={(e) => setSequelTitle(e.target.value)}
                                        placeholder="Titel des nächsten Bandes..."
                                        required
                                        className="w-full bg-surface border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors"
                                    />
                                </div>

                                <div className="space-y-1">
                                    <label className="text-xs font-semibold text-slate-300">Band-Bezeichnung</label>
                                    <input 
                                        type="text"
                                        value={sequelSubtitle}
                                        onChange={(e) => setSequelSubtitle(e.target.value)}
                                        placeholder={`Band ${nextVolumeNum}`}
                                        className="w-full bg-surface border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors"
                                    />
                                </div>
                            </div>

                            <div className="space-y-1">
                                <label className="text-xs font-semibold text-slate-300">Handlung & Prämisse dieses Bandes *</label>
                                <textarea 
                                    value={sequelPrompt}
                                    onChange={(e) => setSequelPrompt(e.target.value)}
                                    placeholder="Worum geht es in diesem Band? Welcher neue Konflikt entsteht?"
                                    required
                                    rows={3}
                                    className="w-full bg-surface border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors resize-none leading-relaxed"
                                />
                            </div>

                            {/* Auto Evolve Characters Toggle */}
                            <div className="p-3 bg-surface/70 rounded-2xl border border-slate-800 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Users className="w-4 h-4 text-indigo-400" />
                                    <div>
                                        <h4 className="text-xs font-semibold text-white">Stamm-Charaktere weiterentwickeln</h4>
                                        <p className="text-[11px] text-text-muted">Aktualisiert Beziehungen/Traumata und schlägt 2-3 neue Figuren vor.</p>
                                    </div>
                                </div>
                                <input 
                                    type="checkbox"
                                    checked={autoEvolveChars}
                                    onChange={(e) => setAutoEvolveChars(e.target.checked)}
                                    className="w-4 h-4 accent-indigo-600 rounded cursor-pointer"
                                />
                            </div>

                            {/* Actions */}
                            <div className="flex justify-end gap-3 pt-2">
                                <button 
                                    type="button"
                                    onClick={() => setShowSequelModal(false)}
                                    disabled={isCreatingSequel}
                                    className="px-4 py-2.5 bg-surface hover:bg-slate-800 text-slate-300 rounded-xl text-xs font-medium border border-slate-700 transition-colors"
                                >
                                    Abbrechen
                                </button>
                                <button 
                                    type="submit"
                                    disabled={isCreatingSequel}
                                    className="btn-primary px-6 py-2.5 text-xs font-semibold rounded-xl flex items-center gap-2 shadow-lg shadow-indigo-500/25"
                                >
                                    {isCreatingSequel ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                                    Band {nextVolumeNum} anlegen & schreiben
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

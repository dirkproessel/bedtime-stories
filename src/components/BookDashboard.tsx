import React, { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { Plus, BookOpen, Trash2, ArrowRight, Loader2, RefreshCw, ArrowLeft } from 'lucide-react';
import BookEditor from './BookEditor';
import { createProBook, deleteProBook } from '../lib/api';
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
        isLoading,
        setActiveView
    } = useStore();
    
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [title, setTitle] = useState('');
    const [prompt, setPrompt] = useState('');
    const [genre, setGenre] = useState('Fantasy');
    const [style, setStyle] = useState('adams');
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Initial load and periodic polling for generating status
    useEffect(() => {
        loadProProjects();
    }, [loadProProjects]);

    // Simple status polling if any project is in "generating" status
    useEffect(() => {
        const hasGenerating = proProjects.some(p => p.status === 'generating');
        if (!hasGenerating) return;

        const interval = setInterval(() => {
            loadProProjects();
        }, 3000);

        return () => clearInterval(interval);
    }, [proProjects, loadProProjects]);

    const handleCreateProject = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!title.trim() || !prompt.trim()) {
            toast.error('Bitte Titel und Beschreibung ausfüllen');
            return;
        }

        setIsSubmitting(true);
        try {
            const newProject = await createProBook({ title, prompt, genre, style });
            toast.success('Projekt erfolgreich angelegt!');
            setTitle('');
            setPrompt('');
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

    if (currentProProject) {
        return (
            <BookEditor 
                project={currentProProject} 
                onBack={() => {
                    setCurrentProProject(null);
                    loadProProjects();
                }} 
            />
        );
    }

    return (
        <div className="space-y-6">
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
                        <h2 className="text-xl font-bold text-white">Projekte ({proProjects.length})</h2>
                        <p className="text-xs text-text-muted mt-1">Erstelle und verwalte deine langen Buchprojekte (Novellen).</p>
                    </div>
                </div>
                
                <div className="flex gap-2">
                    <button 
                        onClick={() => loadProProjects()} 
                        className="p-2.5 bg-surface rounded-xl hover:bg-slate-800 text-slate-300 transition-colors border border-slate-800"
                        title="Aktualisieren"
                    >
                        <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                    </button>
                    <button 
                        onClick={() => setShowCreateModal(true)}
                        className="btn-primary py-2.5 px-5 text-sm flex items-center gap-2 rounded-xl"
                    >
                        <Plus className="w-4 h-4" />
                        Neues Buchprojekt
                    </button>
                </div>
            </div>

            {/* Project List */}
            {proProjects.length === 0 ? (
                <div className="text-center py-20 bg-surface/50 border border-slate-800 rounded-3xl space-y-4">
                    <BookOpen className="w-12 h-12 text-slate-600 mx-auto" />
                    <div>
                        <h3 className="text-white font-medium">Bislang keine Buchprojekte vorhanden</h3>
                        <p className="text-xs text-text-muted mt-1">Klicke auf 'Neues Buchprojekt' um deinen ersten Kurzroman zu starten.</p>
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
                                        <h3 className="font-semibold text-white text-base group-hover:text-primary transition-colors line-clamp-1">
                                            {p.title}
                                        </h3>
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
                                            {p.genre} &bull; {formatAuthorStyles(p.style)}
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
                                <label className="text-xs font-medium text-slate-300">Konzept / Kernidee</label>
                                <textarea 
                                    value={prompt}
                                    onChange={(e) => setPrompt(e.target.value)}
                                    rows={4}
                                    className="w-full bg-background border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-primary resize-none"
                                    placeholder="Worum soll es in dem Buch gehen? Details zur Handlung, Überraschungen, roter Faden..."
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
                                    <label className="text-xs font-medium text-slate-300">Autorenstil</label>
                                    <select 
                                        value={style}
                                        onChange={(e) => setStyle(e.target.value)}
                                        className="w-full bg-background border border-slate-800 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary"
                                    >
                                        {AUTHORS.map(s => (
                                            <option key={s.id} value={s.id}>{s.name} ({s.desc})</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

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

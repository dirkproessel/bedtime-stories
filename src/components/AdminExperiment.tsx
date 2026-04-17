import { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { Sparkles, Loader2, Search, History, CheckCircle2, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { getThumbUrl, adminAnalyzeStory } from '../lib/api';

interface AnalysisResult {
    story_id: string;
    title: string;
    current_synopsis: string;
    new_synopsis: string;
    highlights: string;
}

export default function AdminExperiment() {
    const { stories, loadStories, updateStory, selectedStoryId, setSelectedStoryId } = useStore();
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        // Ensure stories are loaded for selection
        loadStories(1);
    }, []);

    // Reset result when selected story changes
    useEffect(() => {
        setResult(null);
    }, [selectedStoryId]);

    const filteredStories = stories.filter(s => 
        s.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.id.toLowerCase().includes(searchTerm.toLowerCase())
    ).slice(0, 10);

    const handleAnalyze = async () => {
        if (!selectedStoryId) return;
        setIsAnalyzing(true);
        setResult(null);
        try {
            const data = await adminAnalyzeStory(selectedStoryId);
            setResult(data);
            toast.success('Analyse abgeschlossen!');
        } catch (error: any) {
            toast.error(error.message || 'Fehler bei der Analyse');
        } finally {
            setIsAnalyzing(false);
        }
    };

    const handleSave = async () => {
        if (!result) return;
        setIsSaving(true);
        try {
            await updateStory(result.story_id, {
                title: result.title,
                description: result.new_synopsis,
                highlights: result.highlights
            });
            
            toast.success('Änderungen gespeichert!');
            // Update local state by reloading or direct store update is handled by updateStory
            loadStories(1);
        } catch (error: any) {
            toast.error(error.message || 'Fehler beim Speichern');
        } finally {
            setIsSaving(false);
        }
    };

    const selectedStory = stories.find(s => s.id === selectedStoryId);

    return (
        <div className="space-y-8 pb-20">
            <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-xl">
                <div className="flex items-center gap-3 mb-6">
                    <div className="w-12 h-12 bg-primary/10 rounded-2xl flex items-center justify-center text-primary">
                        <Sparkles className="w-6 h-6" />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-white">Story Analyse Labor</h2>
                        <p className="text-slate-400 text-sm">Prüfe die neue KI-Zusammenfassung und Highlights für bestehende Geschichten.</p>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-end">
                    <div className="space-y-2">
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-widest ml-1">Geschichte auswählen</label>
                        <div className="relative">
                            <input 
                                type="text"
                                placeholder="Titel suchen..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-4 py-3.5 pr-10 text-white outline-none focus:border-primary transition-all text-sm"
                            />
                            <Search className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
                        </div>
                        {searchTerm && (
                            <div className="mt-2 bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden divide-y divide-slate-800 absolute z-10 w-full shadow-2xl">
                                {filteredStories.map(s => (
                                    <button
                                        key={s.id}
                                        onClick={() => {
                                            setSelectedStoryId(s.id);
                                            setSearchTerm('');
                                            setResult(null);
                                        }}
                                        className="w-full px-4 py-3 text-left hover:bg-slate-900 transition-colors flex items-center justify-between group"
                                    >
                                        <div className="flex items-center gap-3">
                                            <img src={getThumbUrl(s.id, s.updated_at)} className="w-8 h-8 rounded-lg object-cover" />
                                            <span className="text-sm text-slate-300 group-hover:text-white truncate">{s.title}</span>
                                        </div>
                                        <span className="text-[10px] text-slate-600 font-mono">{s.id}</span>
                                    </button>
                                ))}
                                {filteredStories.length === 0 && (
                                    <div className="px-4 py-3 text-slate-500 text-sm italic">Keine Geschichte gefunden</div>
                                )}
                            </div>
                        )}
                    </div>

                    <button
                        onClick={handleAnalyze}
                        disabled={!selectedStoryId || isAnalyzing}
                        className="w-full flex items-center justify-center gap-3 bg-primary text-white py-4 rounded-2xl font-bold shadow-lg shadow-primary/20 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                        {isAnalyzing ? (
                            <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                            <Sparkles className="w-5 h-5" />
                        )}
                        Analyse starten
                    </button>
                </div>

                {selectedStory && !result && !isAnalyzing && (
                    <div className="mt-8 flex items-center gap-4 p-4 bg-slate-950/50 rounded-2xl border border-slate-800/50">
                        <img src={getThumbUrl(selectedStory.id, selectedStory.updated_at)} className="w-16 h-16 rounded-xl object-cover shadow-lg" />
                        <div className="flex-1 min-w-0">
                            <h3 className="font-bold text-white truncate">{selectedStory.title}</h3>
                            <p className="text-xs text-slate-500 mt-1 line-clamp-1 italic">"{selectedStory.description}"</p>
                        </div>
                    </div>
                )}
            </div>

            {result && (
                <div className="grid grid-cols-1 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Old Synopsis */}
                        <div className="bg-slate-900/40 border border-slate-800/80 rounded-3xl p-6">
                            <div className="flex items-center gap-2 mb-4 text-slate-500">
                                <History className="w-4 h-4" />
                                <span className="text-xs font-bold uppercase tracking-widest">Aktuelle Zusammenfassung</span>
                            </div>
                            <p className="text-sm text-slate-400 leading-relaxed italic border-l-2 border-slate-800 pl-4">
                                {result.current_synopsis}
                            </p>
                        </div>

                        {/* New Synopsis */}
                        <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-3xl p-6 relative overflow-hidden group">
                           <div className="absolute top-0 right-0 p-3 opacity-10">
                               <Sparkles className="w-12 h-12 text-emerald-500" />
                           </div>
                            <div className="flex items-center gap-2 mb-4 text-emerald-500">
                                <Sparkles className="w-4 h-4" />
                                <span className="text-xs font-bold uppercase tracking-widest">Neue KI-Zusammenfassung</span>
                            </div>
                            <p className="text-sm text-slate-200 leading-relaxed font-medium">
                                {result.new_synopsis}
                            </p>
                        </div>
                    </div>

                    {/* Highlights */}
                    <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-6">
                        <div className="flex items-center gap-2 mb-4 text-primary">
                            <CheckCircle2 className="w-4 h-4" />
                            <span className="text-xs font-bold uppercase tracking-widest">Highlights & Punchlines</span>
                        </div>
                        <div className="p-4 bg-slate-950 rounded-2xl border border-white/5 text-lg font-serif italic text-primary/90 text-center leading-relaxed">
                            {result.highlights}
                        </div>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-4 pt-4">
                        <button
                            onClick={handleSave}
                            disabled={isSaving}
                            className="flex-1 flex items-center justify-center gap-3 bg-white text-slate-950 py-4 rounded-2xl font-bold shadow-xl hover:bg-slate-100 active:scale-95 transition-all"
                        >
                            {isSaving ? <Loader2 className="w-5 h-5 animate-spin" /> : <CheckCircle2 className="w-5 h-5" />}
                            Änderungen übernehmen
                        </button>
                        <button
                            onClick={() => setResult(null)}
                            className="px-8 py-4 bg-slate-800 text-slate-300 rounded-2xl font-bold hover:bg-slate-700 transition-all border border-slate-700"
                        >
                            Verwerfen
                        </button>
                    </div>

                    <div className="flex items-start gap-3 p-4 bg-blue-500/10 rounded-2xl border border-blue-500/20 text-blue-300 text-xs leading-relaxed">
                        <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                        <p>
                            Das Übernehmen aktualisiert die Datenbankbeschreibung und fügt die Highlights hinzu. 
                            Dies wirkt sich sofort auf die Story-Cards im Archiv aus.
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}

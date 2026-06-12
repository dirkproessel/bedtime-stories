import React, { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { 
    BookProjectDetail, 
    BookChapter, 
    LektoratFinding, 
    KdpMetadata,
    updateProBook, 
    suggestProCharacters,
    generateProOutline, 
    updateProOutline,
    generateProChapter, 
    updateProChapter,
    proofreadProChapter, 
    generateProCover,
    getProCoverUrl, 
    getProEpubUrl,
    fetchProKdpMetadata
} from '../lib/api';
import { 
    ArrowLeft, 
    Save, 
    Sparkles, 
    FileText, 
    BookOpen, 
    Clipboard, 
    Download, 
    Check, 
    Loader2, 
    AlertTriangle,
    CheckCircle,
    Maximize2,
    VolumeX
} from 'lucide-react';
import toast from 'react-hot-toast';

interface BookEditorProps {
    project: BookProjectDetail;
    onBack: () => void;
}

type StepType = 'concept' | 'outline' | 'writing' | 'lektorat' | 'export';

export default function BookEditor({ project, onBack }: BookEditorProps) {
    const { loadProProjectDetail, currentProProject } = useStore();
    const activeProject = currentProProject || project;

    const [activeStep, setActiveStep] = useState<StepType>('concept');
    const [isSaving, setIsSaving] = useState(false);
    const [isAiLoading, setIsAiLoading] = useState(false);

    // Step 1 State: Concept & Characters
    const [charBible, setCharBible] = useState(activeProject.characters_bible || '');
    const [charModel, setCharModel] = useState('gemini-3.1-flash-lite');

    // Step 2 State: Outline
    const [numChapters, setNumChapters] = useState(activeProject.chapters.length || 8);
    const [outlineModel, setOutlineModel] = useState('gemini-3.1-flash-lite');
    const [editableChapters, setEditableChapters] = useState<any[]>([]);

    // Step 3 State: Writing
    const [selectedChapterNum, setSelectedChapterNum] = useState<number>(1);
    const [writingModel, setWritingModel] = useState('deepseek-v4-pro');
    const [chapterText, setChapterText] = useState('');
    const [chapterTitle, setChapterTitle] = useState('');
    const [chapterOutline, setChapterOutline] = useState('');
    const [feedback, setFeedback] = useState('');

    // Step 4 State: Lektorat
    const [lektoratModel, setLektoratModel] = useState('gemini-3.5-flash');
    const [findings, setFindings] = useState<LektoratFinding[]>([]);

    // Step 5 State: Export & Cover
    const [coverPrompt, setCoverPrompt] = useState(activeProject.cover_prompt || '');
    const [coverVersion, setCoverVersion] = useState(Date.now().toString());
    const [kdpMetadata, setKdpMetadata] = useState<KdpMetadata | null>(null);
    const [kdpModel, setKdpModel] = useState('gemini-3.1-flash-lite');

    // Reload active project context when step changes to keep it fresh
    useEffect(() => {
        loadProProjectDetail(activeProject.id);
    }, [activeStep, loadProProjectDetail, activeProject.id]);

    // Synchronize editable chapters for outline editing
    useEffect(() => {
        if (activeProject.outline) {
            try {
                const data = JSON.parse(activeProject.outline);
                setEditableChapters(data.chapters || []);
            } catch (e) {
                // Fallback
                setEditableChapters(activeProject.chapters.map(c => ({
                    chapter_number: c.chapter_number,
                    title: c.title,
                    plot_outline: c.plot_outline
                })));
            }
        } else {
            setEditableChapters(activeProject.chapters.map(c => ({
                chapter_number: c.chapter_number,
                title: c.title,
                plot_outline: c.plot_outline
            })));
        }
    }, [activeProject]);

    // Sync selected chapter content when selected chapter changes
    useEffect(() => {
        const chap = activeProject.chapters.find(c => c.chapter_number === selectedChapterNum);
        if (chap) {
            setChapterText(chap.content || '');
            setChapterTitle(chap.title || '');
            setChapterOutline(chap.plot_outline || '');
        } else {
            setChapterText('');
            setChapterTitle('');
            setChapterOutline('');
        }
        setFindings([]); // Clear proofread findings when switching chapters
    }, [selectedChapterNum, activeProject]);

    // Handle project status polling during background tasks
    useEffect(() => {
        if (activeProject.status !== 'generating') return;

        const timer = setInterval(() => {
            loadProProjectDetail(activeProject.id);
            // If the cover was generating and is now finished, update cover image key
            if (activeProject.status === 'generating' && activeProject.progress?.includes('Cover')) {
                setCoverVersion(Date.now().toString());
            }
        }, 3000);

        return () => clearInterval(timer);
    }, [activeProject.status, activeProject.id, activeProject.progress, loadProProjectDetail]);


    // --- Step 1 Actions ---

    const handleSaveCharacters = async () => {
        setIsSaving(true);
        try {
            await updateProBook(activeProject.id, { characters_bible: charBible });
            toast.success('Charakter-Bible gespeichert!');
        } catch (e: any) {
            toast.error('Fehler beim Speichern: ' + e.message);
        } finally {
            setIsSaving(false);
        }
    };

    const handleSuggestCharacters = async () => {
        setIsAiLoading(true);
        try {
            toast.loading('Generiere Charakter-Vorschläge...', { id: 'ai' });
            const res = await suggestProCharacters(activeProject.id, charModel);
            
            // Format suggestions as markdown/plain text for copy-paste
            const formatted = res.suggestions.map((c: any) => {
                return `**${c.name}** (${c.role})\nCharakterzug: ${c.traits.join(', ')}\nBeschreibung: ${c.description}\n`;
            }).join('\n---\n\n');
            
            setCharBible(prev => (prev ? prev + '\n\n' : '') + formatted);
            toast.success('Vorschläge generiert und unten angehängt!', { id: 'ai' });
        } catch (e: any) {
            toast.error('Fehler: ' + e.message, { id: 'ai' });
        } finally {
            setIsAiLoading(false);
        }
    };


    // --- Step 2 Actions ---

    const handleGenerateOutline = async () => {
        setIsAiLoading(true);
        try {
            toast.loading('Gliederung wird erstellt...', { id: 'ai' });
            await generateProOutline(activeProject.id, numChapters, outlineModel);
            toast.success('Outline erfolgreich erstellt!', { id: 'ai' });
            await loadProProjectDetail(activeProject.id);
        } catch (e: any) {
            toast.error('Fehler: ' + e.message, { id: 'ai' });
        } finally {
            setIsAiLoading(false);
        }
    };

    const handleSaveOutline = async () => {
        setIsSaving(true);
        try {
            await updateProOutline(activeProject.id, editableChapters);
            toast.success('Gliederung erfolgreich aktualisiert!');
            await loadProProjectDetail(activeProject.id);
        } catch (e: any) {
            toast.error('Fehler beim Speichern: ' + e.message);
        } finally {
            setIsSaving(false);
        }
    };

    const updateEditableChapterField = (num: number, field: string, value: string) => {
        setEditableChapters(prev => prev.map(c => 
            c.chapter_number === num ? { ...c, [field]: value } : c
        ));
    };


    // --- Step 3 Actions ---

    const handleGenerateChapter = async (useFeedback: boolean = false) => {
        setIsAiLoading(true);
        try {
            toast.loading('Kapitel-Generierung gestartet...', { id: 'ai' });
            await generateProChapter(
                activeProject.id, 
                selectedChapterNum, 
                writingModel, 
                useFeedback ? feedback : undefined
            );
            toast.success('Erstellung läuft im Hintergrund!', { id: 'ai' });
            if (useFeedback) setFeedback('');
            await loadProProjectDetail(activeProject.id);
        } catch (e: any) {
            toast.error('Fehler: ' + e.message, { id: 'ai' });
        } finally {
            setIsAiLoading(false);
        }
    };

    const handleSaveChapterContent = async () => {
        setIsSaving(true);
        try {
            await updateProChapter(activeProject.id, selectedChapterNum, {
                title: chapterTitle,
                plot_outline: chapterOutline,
                content: chapterText
            });
            toast.success('Kapitel-Text gespeichert!');
            await loadProProjectDetail(activeProject.id);
        } catch (e: any) {
            toast.error('Fehler beim Speichern: ' + e.message);
        } finally {
            setIsSaving(false);
        }
    };


    // --- Step 4 Actions ---

    const handleRunLektorat = async () => {
        setIsAiLoading(true);
        try {
            toast.loading('Lektorat läuft über Kapitel ' + selectedChapterNum + '...', { id: 'ai' });
            const res = await proofreadProChapter(activeProject.id, selectedChapterNum, lektoratModel);
            setFindings(res.findings);
            if (res.findings.length === 0) {
                toast.success('Keine auffälligen Fehler gefunden!', { id: 'ai' });
            } else {
                toast.success(`${res.findings.length} Korrekturvorschläge gefunden!`, { id: 'ai' });
            }
        } catch (e: any) {
            toast.error('Fehler: ' + e.message, { id: 'ai' });
        } finally {
            setIsAiLoading(false);
        }
    };

    const handleApplyFinding = async (finding: LektoratFinding) => {
        // Find position of original snippet in text
        const index = chapterText.indexOf(finding.original_snippet);
        if (index === -1) {
            toast.error('Textstelle im Editor nicht gefunden. Eventuell bereits editiert?');
            return;
        }

        const newText = chapterText.replace(finding.original_snippet, finding.suggested_rewrite);
        setChapterText(newText);
        
        // Remove finding from list
        setFindings(prev => prev.filter(f => f !== finding));
        toast.success('Korrektur im Editor angewendet. Speichern nicht vergessen!');
    };


    // --- Step 5 Actions ---

    const handleGenerateCover = async () => {
        if (!coverPrompt.trim()) {
            toast.error('Bitte beschreibe erst ein Motiv für das Cover.');
            return;
        }
        setIsAiLoading(true);
        try {
            toast.loading('Cover-Erstellung läuft im Hintergrund...', { id: 'ai' });
            await generateProCover(activeProject.id, coverPrompt);
            toast.success('Generierung gestartet!', { id: 'ai' });
        } catch (e: any) {
            toast.error('Fehler: ' + e.message, { id: 'ai' });
        } finally {
            setIsAiLoading(false);
        }
    };

    const handleFetchKdpMetadata = async () => {
        setIsAiLoading(true);
        try {
            toast.loading('KDP-Metadaten werden analysiert...', { id: 'ai' });
            const meta = await fetchProKdpMetadata(activeProject.id, kdpModel);
            setKdpMetadata(meta);
            toast.success('Metadaten geladen!', { id: 'ai' });
        } catch (e: any) {
            toast.error('Fehler: ' + e.message, { id: 'ai' });
        } finally {
            setIsAiLoading(false);
        }
    };

    const copyToClipboard = (text: string, label: string) => {
        navigator.clipboard.writeText(text);
        toast.success(`${label} kopiert!`);
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-5">
                <div className="flex items-center gap-4">
                    <button 
                        onClick={onBack}
                        className="p-2 bg-surface hover:bg-slate-800 text-slate-400 hover:text-white rounded-xl transition-colors border border-slate-800"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </button>
                    <div>
                        <div className="flex items-center gap-2">
                            <span className="text-[10px] uppercase font-mono tracking-wider bg-primary/10 text-primary px-2.5 py-0.5 rounded-full border border-primary/20">Pro Mode</span>
                            {activeProject.status === 'generating' && (
                                <span className="text-[10px] uppercase font-mono tracking-wider bg-amber-500/10 text-amber-400 px-2.5 py-0.5 rounded-full border border-amber-500/20 animate-pulse flex items-center gap-1">
                                    <Loader2 className="w-2.5 h-2.5 animate-spin" />
                                    Verarbeitung läuft
                                </span>
                            )}
                        </div>
                        <h2 className="text-xl font-bold text-white mt-1.5">{activeProject.title}</h2>
                    </div>
                </div>

                {/* Info Progress Panel */}
                {activeProject.status === 'generating' && (
                    <div className="bg-surface/50 px-4 py-3 rounded-2xl border border-slate-800/80 flex items-center gap-3 w-full sm:w-auto">
                        <Loader2 className="w-5 h-5 text-primary animate-spin shrink-0" />
                        <div className="text-xs">
                            <div className="font-semibold text-slate-200">
                                {activeProject.progress || 'KI arbeitet...'}
                            </div>
                            <div className="text-[10px] text-text-muted mt-0.5">
                                Fortschritt: {activeProject.progress_pct}%
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Steps Navigation Bar */}
            <div className="flex bg-surface/50 border border-slate-800 p-1 rounded-2xl overflow-x-auto no-scrollbar gap-1">
                {[
                    { id: 'concept', label: '1. Konzept & Charaktere' },
                    { id: 'outline', label: '2. Kapitel-Gliederung' },
                    { id: 'writing', label: '3. Kapitel schreiben' },
                    { id: 'lektorat', label: '4. Lektorat' },
                    { id: 'export', label: '5. Cover & Export' }
                ].map((step) => (
                    <button
                        key={step.id}
                        onClick={() => setActiveStep(step.id as StepType)}
                        className={`px-4 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all flex-1 ${
                            activeStep === step.id 
                            ? 'bg-slate-800 text-white shadow-sm border border-slate-700/50' 
                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/20'
                        }`}
                    >
                        {step.label}
                    </button>
                ))}
            </div>

            {/* STEP 1: CONCEPT & CHARACTERS */}
            {activeStep === 'concept' && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-1 space-y-4">
                        <div className="bg-surface p-5 rounded-3xl border border-slate-800 space-y-3">
                            <h3 className="font-semibold text-white text-sm">Projektdaten</h3>
                            <div className="text-xs space-y-2.5">
                                <div>
                                    <span className="text-slate-500 block uppercase font-mono text-[9px]">Ziel-Wortanzahl</span>
                                    <span className="text-slate-300 font-medium">15.000 - 20.000 Wörter (Kurzroman)</span>
                                </div>
                                <div>
                                    <span className="text-slate-500 block uppercase font-mono text-[9px]">Genre</span>
                                    <span className="text-slate-300 font-medium">{activeProject.genre}</span>
                                </div>
                                <div>
                                    <span className="text-slate-500 block uppercase font-mono text-[9px]">Schreibstil</span>
                                    <span className="text-slate-300 font-medium">{activeProject.style}</span>
                                </div>
                                <div>
                                    <span className="text-slate-500 block uppercase font-mono text-[9px]">Buchidee</span>
                                    <p className="text-slate-400 leading-relaxed mt-0.5">{activeProject.prompt}</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="lg:col-span-2 bg-surface p-5 rounded-3xl border border-slate-800 space-y-4">
                        <div className="flex justify-between items-center">
                            <h3 className="font-semibold text-white text-sm">Charakter-Bible</h3>
                            
                            <div className="flex items-center gap-2">
                                <select 
                                    value={charModel}
                                    onChange={(e) => setCharModel(e.target.value)}
                                    className="bg-background border border-slate-800 text-xs text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
                                >
                                    <option value="gemini-3.1-flash-lite">Gemini Flash Lite</option>
                                    <option value="gemini-3.5-flash">Gemini 3.5 Flash</option>
                                </select>
                                <button 
                                    onClick={handleSuggestCharacters}
                                    disabled={isAiLoading}
                                    className="text-xs bg-slate-800 hover:bg-slate-700 text-primary border border-slate-700/50 rounded-lg px-3 py-1 flex items-center gap-1 transition-colors"
                                >
                                    <Sparkles className="w-3 h-3" />
                                    KI-Vorschlag
                                </button>
                            </div>
                        </div>

                        <textarea 
                            value={charBible}
                            onChange={(e) => setCharBible(e.target.value)}
                            rows={12}
                            className="w-full bg-background border border-slate-800 rounded-2xl px-4 py-3 text-xs text-white focus:outline-none focus:border-primary font-mono leading-relaxed"
                            placeholder="Definiere die Charaktere für dein Buch. Du kannst manuell schreiben oder den KI-Vorschlag nutzen, um Figuren und ihre Beziehungen festzuhalten..."
                        />

                        <div className="flex justify-end pt-2">
                            <button 
                                onClick={handleSaveCharacters}
                                disabled={isSaving}
                                className="btn-primary py-2 px-5 text-xs flex items-center gap-1.5 rounded-xl"
                            >
                                {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                                Charakter-Bible speichern
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* STEP 2: OUTLINE EDITOR */}
            {activeStep === 'outline' && (
                <div className="bg-surface p-5 rounded-3xl border border-slate-800 space-y-5">
                    <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 border-b border-slate-800/80 pb-4">
                        <div className="space-y-1">
                            <h3 className="font-semibold text-white text-sm">Buchgliederung & Kapitel</h3>
                            <p className="text-xs text-text-muted">Plane und verfeinere den Handlungsstrang deines Buches vor dem Schreiben.</p>
                        </div>

                        {activeProject.chapters.length === 0 ? (
                            <div className="flex items-center gap-3">
                                <label className="text-xs text-slate-300">Kapitelanzahl:</label>
                                <select 
                                    value={numChapters} 
                                    onChange={(e) => setNumChapters(parseInt(e.target.value))}
                                    className="bg-background border border-slate-800 text-xs text-slate-300 rounded-lg px-2 py-1.5 focus:outline-none"
                                >
                                    {[3, 4, 5, 6, 7, 8, 9, 10, 12].map(n => (
                                        <option key={n} value={n}>{n} Kapitel</option>
                                    ))}
                                </select>
                                <select 
                                    value={outlineModel} 
                                    onChange={(e) => setOutlineModel(e.target.value)}
                                    className="bg-background border border-slate-800 text-xs text-slate-300 rounded-lg px-2 py-1.5 focus:outline-none"
                                >
                                    <option value="gemini-3.1-flash-lite">Gemini Flash Lite</option>
                                    <option value="gemini-3.5-flash">Gemini 3.5 Flash</option>
                                </select>
                                <button 
                                    onClick={handleGenerateOutline}
                                    disabled={isAiLoading}
                                    className="btn-primary py-1.5 px-4 text-xs flex items-center gap-1 rounded-xl"
                                >
                                    Gliederung generieren
                                </button>
                            </div>
                        ) : (
                            <button 
                                onClick={handleSaveOutline}
                                disabled={isSaving}
                                className="btn-primary py-1.5 px-5 text-xs flex items-center gap-1 rounded-xl"
                            >
                                {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                                Gliederung speichern
                            </button>
                        )}
                    </div>

                    {/* Chapter Cards list for editing */}
                    {editableChapters.length === 0 ? (
                        <div className="text-center py-12 text-slate-500 text-xs space-y-2">
                            <BookOpen className="w-8 h-8 mx-auto text-slate-600" />
                            <p>Noch keine Gliederung vorhanden. Wähle die Kapitelanzahl und generiere die Outline.</p>
                        </div>
                    ) : (
                        <div className="space-y-4 max-h-[50vh] overflow-y-auto pr-2 custom-scrollbar">
                            {editableChapters.map((chap, i) => (
                                <div key={i} className="bg-background p-4 rounded-2xl border border-slate-800 space-y-3">
                                    <div className="flex items-center gap-3">
                                        <span className="w-6 h-6 rounded-lg bg-slate-800 flex items-center justify-center font-mono text-xs text-slate-300 shrink-0 font-bold">
                                            {chap.chapter_number}
                                        </span>
                                        <input 
                                            type="text" 
                                            value={chap.title}
                                            onChange={(e) => updateEditableChapterField(chap.chapter_number, 'title', e.target.value)}
                                            className="bg-surface border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-primary w-full max-w-sm"
                                            placeholder="Kapiteltitel"
                                        />
                                    </div>

                                    <textarea 
                                        value={chap.plot_outline}
                                        onChange={(e) => updateEditableChapterField(chap.chapter_number, 'plot_outline', e.target.value)}
                                        rows={2}
                                        className="w-full bg-surface border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-primary resize-none leading-relaxed"
                                        placeholder="Handlungsstrang und Ereignisse für dieses Kapitel..."
                                    />
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* STEP 3: CHAPTER WRITING */}
            {activeStep === 'writing' && (
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                    {/* Chapter selection sidebar */}
                    <div className="lg:col-span-1 space-y-4">
                        <div className="bg-surface p-4 rounded-3xl border border-slate-800 space-y-3">
                            <h3 className="font-semibold text-white text-xs">Kapitelliste</h3>
                            <div className="space-y-1 max-h-[45vh] overflow-y-auto custom-scrollbar">
                                {activeProject.chapters.map((c) => (
                                    <button
                                        key={c.id}
                                        onClick={() => setSelectedChapterNum(c.chapter_number)}
                                        className={`w-full text-left px-3.5 py-2.5 rounded-xl text-xs flex justify-between items-center gap-2 border transition-all ${
                                            selectedChapterNum === c.chapter_number 
                                            ? 'bg-slate-800 border-slate-700/50 text-white font-semibold' 
                                            : 'bg-transparent border-transparent hover:bg-slate-800/10 text-slate-400'
                                        }`}
                                    >
                                        <span className="truncate">Kapitel {c.chapter_number}: {c.title}</span>
                                        <span className={`text-[8px] uppercase tracking-wider px-1.5 py-0.5 rounded-md ${
                                            c.status === 'done' 
                                            ? 'bg-primary/10 text-primary border border-primary/20' 
                                            : c.status === 'generating' 
                                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse' 
                                            : c.status === 'error'
                                            ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                                            : 'bg-slate-800 text-slate-500'
                                        }`}>
                                            {c.status}
                                        </span>
                                    </button>
                                ))}
                            </div>
                        </div>
                        
                        {/* Outline of selected chapter */}
                        <div className="bg-surface p-4 rounded-3xl border border-slate-800 space-y-2">
                            <h4 className="text-xs font-semibold text-white">Kapitel-Plot-Outline</h4>
                            <p className="text-xs text-slate-400 leading-relaxed font-serif">
                                {chapterOutline || 'Keine Plot-Vorgabe für dieses Kapitel.'}
                            </p>
                        </div>
                    </div>

                    {/* Writer Workspace */}
                    <div className="lg:col-span-3 bg-surface p-5 rounded-3xl border border-slate-800 space-y-4">
                        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 border-b border-slate-800 pb-3">
                            <div className="space-y-1">
                                <h3 className="font-semibold text-white text-sm">
                                    Arbeitsbereich Kapitel {selectedChapterNum}
                                </h3>
                                <p className="text-xs text-text-muted">
                                    Wörter: {chapterText ? chapterText.split(/\s+/).filter(Boolean).length : 0}
                                </p>
                            </div>

                            <div className="flex items-center gap-2">
                                <select 
                                    value={writingModel}
                                    onChange={(e) => setWritingModel(e.target.value)}
                                    className="bg-background border border-slate-800 text-xs text-slate-300 rounded-lg px-2 py-1.5 focus:outline-none"
                                >
                                    <option value="deepseek-v4-pro">DeepSeek V4 Pro (Default)</option>
                                    <option value="gemini-3.5-flash">Gemini 3.5 Flash</option>
                                    <option value="deepseek-v4-flash">DeepSeek V4 Flash</option>
                                </select>
                                <button 
                                    onClick={() => handleGenerateChapter(false)}
                                    disabled={isAiLoading || activeProject.status === 'generating'}
                                    className="btn-primary py-1.5 px-4 text-xs flex items-center gap-1 rounded-xl"
                                >
                                    <Sparkles className="w-3.5 h-3.5" />
                                    Text generieren
                                </button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <input 
                                type="text"
                                value={chapterTitle}
                                onChange={(e) => setChapterTitle(e.target.value)}
                                className="w-full bg-background border border-slate-800 rounded-xl px-4 py-2 text-sm text-white font-bold focus:outline-none focus:border-primary"
                                placeholder="Kapiteltitel"
                            />
                            
                            <textarea 
                                value={chapterText}
                                onChange={(e) => setChapterText(e.target.value)}
                                rows={15}
                                className="w-full bg-background border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-200 focus:outline-none focus:border-primary leading-relaxed font-serif custom-scrollbar"
                                placeholder="Der generierte Inhalt wird hier angezeigt und kann editiert werden..."
                            />
                        </div>

                        {/* Rewrite Feedback Box */}
                        <div className="bg-background p-4 rounded-2xl border border-slate-800 space-y-3">
                            <div className="space-y-1">
                                <h4 className="text-xs font-semibold text-white">Regeneration mit Feedback</h4>
                                <p className="text-[10px] text-text-muted">Beschreibe Änderungen, z.B. "Mach das Kapitel spannender" oder "Füge mehr Dialog hinzu".</p>
                            </div>

                            <div className="flex gap-2">
                                <input 
                                    type="text"
                                    value={feedback}
                                    onChange={(e) => setFeedback(e.target.value)}
                                    className="w-full bg-surface border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-primary"
                                    placeholder="z.B. Lass den Hauptcharakter misstrauischer wirken..."
                                />
                                <button
                                    onClick={() => handleGenerateChapter(true)}
                                    disabled={isAiLoading || !feedback.trim() || activeProject.status === 'generating'}
                                    className="bg-slate-800 hover:bg-slate-700 text-amber-400 text-xs px-4 py-2 rounded-xl transition-colors border border-slate-700/50 flex items-center gap-1 shrink-0"
                                >
                                    Regenerieren
                                </button>
                            </div>
                        </div>

                        <div className="flex justify-end pt-2">
                            <button 
                                onClick={handleSaveChapterContent}
                                disabled={isSaving}
                                className="btn-primary py-2 px-5 text-xs flex items-center gap-1.5 rounded-xl"
                            >
                                {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                                Kapitel-Änderungen speichern
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* STEP 4: CROSS-LLM LEKTORAT */}
            {activeStep === 'lektorat' && (
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                    {/* Chapter selector */}
                    <div className="lg:col-span-1 bg-surface p-4 rounded-3xl border border-slate-800 space-y-3">
                        <h3 className="font-semibold text-white text-xs">Kapitelauswahl</h3>
                        <div className="space-y-1">
                            {activeProject.chapters.map((c) => (
                                <button
                                    key={c.id}
                                    onClick={() => setSelectedChapterNum(c.chapter_number)}
                                    className={`w-full text-left px-3.5 py-2.5 rounded-xl text-xs flex justify-between items-center gap-2 border transition-all ${
                                        selectedChapterNum === c.chapter_number 
                                        ? 'bg-slate-800 border-slate-700/50 text-white font-semibold' 
                                        : 'bg-transparent border-transparent hover:bg-slate-800/10 text-slate-400'
                                    }`}
                                >
                                    <span className="truncate">Kapitel {c.chapter_number}: {c.title}</span>
                                    <span className={`text-[8px] uppercase tracking-wider px-1.5 py-0.5 rounded-md ${
                                        c.content ? 'bg-primary/10 text-primary' : 'bg-slate-800 text-slate-500'
                                    }`}>
                                        {c.content ? 'Text da' : 'Leer'}
                                    </span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Proofread results */}
                    <div className="lg:col-span-3 bg-surface p-5 rounded-3xl border border-slate-800 space-y-5">
                        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 border-b border-slate-800 pb-3">
                            <div className="space-y-1">
                                <h3 className="font-semibold text-white text-sm">
                                    Lektoratsprüfung (Kapitel {selectedChapterNum})
                                </h3>
                                <p className="text-xs text-text-muted">Gemini prüft den von DeepSeek geschriebenen Kapiteltext auf Logik und Fehler.</p>
                            </div>

                            <div className="flex items-center gap-2">
                                <select 
                                    value={lektoratModel}
                                    onChange={(e) => setLektoratModel(e.target.value)}
                                    className="bg-background border border-slate-800 text-xs text-slate-300 rounded-lg px-2 py-1.5 focus:outline-none"
                                >
                                    <option value="gemini-3.5-flash">Gemini 3.5 Flash (Beste)</option>
                                    <option value="gemini-3.1-flash-lite">Gemini Flash Lite</option>
                                </select>
                                <button 
                                    onClick={handleRunLektorat}
                                    disabled={isAiLoading || !chapterText}
                                    className="btn-primary py-1.5 px-4 text-xs flex items-center gap-1 rounded-xl"
                                >
                                    <Sparkles className="w-3.5 h-3.5" />
                                    Prüfung starten
                                </button>
                            </div>
                        </div>

                        {/* Editor reference block */}
                        {chapterText && (
                            <div className="bg-background p-3 rounded-2xl border border-slate-800">
                                <h4 className="text-xs font-semibold text-slate-400 mb-1.5">Geladener Kapiteltext (Vorschau):</h4>
                                <div className="text-[11px] text-slate-300 font-serif line-clamp-3 leading-relaxed">
                                    {chapterText}
                                </div>
                            </div>
                        )}

                        {/* Findings layout */}
                        {findings.length === 0 ? (
                            <div className="text-center py-12 text-slate-500 text-xs space-y-2">
                                <CheckCircle className="w-8 h-8 mx-auto text-slate-600" />
                                <p>Keine ungelösten Lektorat-Befunde. Starte die Prüfung über den Button oben.</p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <h4 className="text-xs font-semibold text-white flex items-center gap-2">
                                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                                    Korrektur-Empfehlungen ({findings.length})
                                </h4>

                                <div className="space-y-3 max-h-[40vh] overflow-y-auto pr-1 custom-scrollbar">
                                    {findings.map((f, idx) => (
                                        <div key={idx} className="bg-background p-4.5 rounded-2xl border border-slate-800 space-y-3 text-xs">
                                            <div className="flex justify-between items-start gap-3">
                                                <span className={`px-2 py-0.5 rounded-md font-mono text-[9px] uppercase tracking-wider font-bold ${
                                                    f.category === 'consistency' 
                                                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' 
                                                    : f.category === 'style'
                                                    ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                                    : 'bg-red-500/10 text-red-400 border border-red-500/20'
                                                }`}>
                                                    {f.category}
                                                </span>
                                                <span className="text-[10px] text-slate-500 font-semibold">Empfehlung</span>
                                            </div>

                                            <div className="text-slate-300 font-semibold">
                                                {f.description}
                                            </div>

                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                                                <div className="bg-red-500/5 p-2 rounded-xl border border-red-500/10 space-y-1">
                                                    <span className="text-[9px] font-mono uppercase text-red-400 font-bold">Original:</span>
                                                    <p className="text-[11px] text-slate-400 font-serif leading-relaxed italic">"{f.original_snippet}"</p>
                                                </div>
                                                <div className="bg-primary/5 p-2 rounded-xl border border-primary/10 space-y-1">
                                                    <span className="text-[9px] font-mono uppercase text-primary font-bold">Korrektur:</span>
                                                    <p className="text-[11px] text-slate-300 font-serif leading-relaxed italic">"{f.suggested_rewrite}"</p>
                                                </div>
                                            </div>

                                            {chapterText.includes(f.original_snippet) ? (
                                                <div className="flex justify-end">
                                                    <button
                                                        onClick={() => handleApplyFinding(f)}
                                                        className="bg-primary/15 hover:bg-primary/20 text-primary border border-primary/30 text-[10px] px-3.5 py-1.5 rounded-xl transition-colors font-medium flex items-center gap-1"
                                                    >
                                                        <Check className="w-3.5 h-3.5" />
                                                        Original im Editor ersetzen
                                                    </button>
                                                </div>
                                            ) : (
                                                <div className="text-right text-[10px] text-slate-500 italic">
                                                    Bereits im Kapitel-Editor angepasst oder ersetzt.
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>

                                <div className="bg-amber-500/5 p-3.5 rounded-2xl border border-amber-500/15 flex items-start gap-3">
                                    <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                                    <p className="text-[10px] text-slate-400 leading-normal">
                                        <b>Wichtiger Hinweis:</b> Wenn du Korrekturen mit 'Original im Editor ersetzen' anwendest, 
                                        musst du danach im Tab <b>"3. Kapitel schreiben"</b> auf <b>"Kapitel-Änderungen speichern"</b> klicken, 
                                        um die Änderungen fest in der Datenbank zu hinterlegen!
                                    </p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* STEP 5: COVER & EXPORT */}
            {activeStep === 'export' && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Cover Generator Panel */}
                    <div className="lg:col-span-1 bg-surface p-5 rounded-3xl border border-slate-800 space-y-4">
                        <h3 className="font-semibold text-white text-sm">Cover-Erstellung (KDP-Format)</h3>
                        
                        {activeProject.cover_image_url ? (
                            <div className="space-y-3">
                                <div className="aspect-[2/3] w-full bg-background rounded-2xl border border-slate-800 overflow-hidden shadow-inner flex items-center justify-center relative group">
                                    <img 
                                        src={`${getProCoverUrl(activeProject.id)}?v=${coverVersion}`}
                                        alt="Buch Cover"
                                        className="w-full h-full object-cover"
                                    />
                                    <div className="absolute inset-0 bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                                        <a 
                                            href={`${getProCoverUrl(activeProject.id)}?v=${coverVersion}`}
                                            target="_blank" 
                                            rel="noreferrer"
                                            className="p-3 bg-slate-800 rounded-xl hover:bg-slate-700 text-white flex items-center gap-1.5 text-xs transition-colors"
                                        >
                                            <Maximize2 className="w-4 h-4" />
                                            Vollbild öffnen
                                        </a>
                                    </div>
                                </div>
                                <p className="text-[10px] text-center text-slate-500 italic">Aspect Ratio: 2:3 (Für Amazon 6x9" optimal)</p>
                            </div>
                        ) : (
                            <div className="aspect-[2/3] w-full bg-background/50 rounded-2xl border border-slate-800 border-dashed flex flex-col items-center justify-center p-6 text-center text-slate-600 space-y-2">
                                <BookOpen className="w-8 h-8" />
                                <p className="text-xs">Noch kein Cover generiert.</p>
                            </div>
                        )}

                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-slate-300">Bild-Prompt (Editierbar):</label>
                            <textarea 
                                value={coverPrompt}
                                onChange={(e) => setCoverPrompt(e.target.value)}
                                rows={4}
                                className="w-full bg-background border border-slate-800 rounded-2xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-primary resize-none font-serif leading-relaxed"
                                placeholder="z. B. Ein mystischer Wald im Mondlicht, Ölgemälde, weiches Licht, hoher Kontrast..."
                            />
                        </div>

                        <button 
                            onClick={handleGenerateCover}
                            disabled={isAiLoading || activeProject.status === 'generating'}
                            className="w-full btn-primary py-2.5 text-xs flex items-center justify-center gap-2 rounded-xl"
                        >
                            <Sparkles className="w-4 h-4" />
                            Cover generieren
                        </button>
                    </div>

                    {/* Metadata & EPUB export panel */}
                    <div className="lg:col-span-2 space-y-6">
                        {/* EPUB Download box */}
                        <div className="bg-surface p-5 rounded-3xl border border-slate-800 space-y-4">
                            <h3 className="font-semibold text-white text-sm">Dateiexport</h3>
                            <p className="text-xs text-text-muted">Exportiere dein fertiges Buch als Kindle-kompatible EPUB-Datei.</p>
                            
                            <div className="flex flex-col sm:flex-row gap-4 items-stretch sm:items-center">
                                <a 
                                    href={getProEpubUrl(activeProject.id)}
                                    className="btn-primary py-3 px-6 text-sm font-semibold rounded-2xl flex items-center justify-center gap-2 flex-1 sm:flex-initial"
                                >
                                    <Download className="w-5 h-5" />
                                    EPUB Datei herunterladen
                                </a>
                            </div>
                        </div>

                        {/* Amazon KDP metadata copy-paste sheet */}
                        <div className="bg-surface p-5 rounded-3xl border border-slate-800 space-y-4">
                            <div className="flex justify-between items-center border-b border-slate-800/80 pb-3">
                                <div className="space-y-0.5">
                                    <h3 className="font-semibold text-white text-sm">Amazon KDP Metadaten</h3>
                                    <p className="text-xs text-text-muted">Kopiere diese Daten direkt in dein Amazon KDP Dashboard.</p>
                                </div>
                                
                                <div className="flex items-center gap-2">
                                    <select 
                                        value={kdpModel}
                                        onChange={(e) => setKdpModel(e.target.value)}
                                        className="bg-background border border-slate-800 text-xs text-slate-300 rounded-lg px-2 py-1.5 focus:outline-none"
                                    >
                                        <option value="gemini-3.1-flash-lite">Gemini Flash Lite</option>
                                        <option value="gemini-3.5-flash">Gemini 3.5 Flash</option>
                                    </select>
                                    <button 
                                        onClick={handleFetchKdpMetadata}
                                        disabled={isAiLoading}
                                        className="bg-slate-800 hover:bg-slate-700 text-primary border border-slate-700/50 text-xs px-3 py-1.5 rounded-xl transition-colors font-medium flex items-center gap-1.5 shrink-0"
                                    >
                                        {isAiLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                                        Metadaten erstellen
                                    </button>
                                </div>
                            </div>

                            {kdpMetadata ? (
                                <div className="space-y-4 text-xs">
                                    <div className="space-y-1 relative">
                                        <div className="flex justify-between items-center">
                                            <span className="text-[10px] uppercase font-mono text-slate-500 font-semibold">Buchtitel (Zur Referenz):</span>
                                            <button 
                                                onClick={() => copyToClipboard(activeProject.title, 'Buchtitel')}
                                                className="text-slate-500 hover:text-white p-1 hover:bg-slate-800 rounded-lg transition-colors"
                                                title="Titel kopieren"
                                            >
                                                <Clipboard className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                        <div className="bg-background border border-slate-800 rounded-xl p-3 text-slate-200">
                                            {activeProject.title}
                                        </div>
                                    </div>

                                    <div className="space-y-1">
                                        <div className="flex justify-between items-center">
                                            <span className="text-[10px] uppercase font-mono text-slate-500 font-semibold">Empfohlener Untertitel:</span>
                                            <button 
                                                onClick={() => copyToClipboard(kdpMetadata.suggested_subtitle, 'Untertitel')}
                                                className="text-slate-500 hover:text-white p-1 hover:bg-slate-800 rounded-lg transition-colors"
                                                title="Untertitel kopieren"
                                            >
                                                <Clipboard className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                        <div className="bg-background border border-slate-800 rounded-xl p-3 text-slate-200 font-serif">
                                            {kdpMetadata.suggested_subtitle}
                                        </div>
                                    </div>

                                    <div className="space-y-1">
                                        <div className="flex justify-between items-center">
                                            <span className="text-[10px] uppercase font-mono text-slate-500 font-semibold">KDP-Buchbeschreibung (HTML):</span>
                                            <button 
                                                onClick={() => copyToClipboard(kdpMetadata.description_kdp, 'Buchbeschreibung')}
                                                className="text-slate-500 hover:text-white p-1 hover:bg-slate-800 rounded-lg transition-colors"
                                                title="Beschreibung kopieren"
                                            >
                                                <Clipboard className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                        <textarea
                                            readOnly
                                            value={kdpMetadata.description_kdp}
                                            rows={5}
                                            className="w-full bg-background border border-slate-800 rounded-xl p-3 text-slate-300 font-mono focus:outline-none resize-none leading-relaxed"
                                        />
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div className="space-y-1">
                                            <span className="text-[10px] uppercase font-mono text-slate-500 font-semibold block">7 Such-Keywords:</span>
                                            <div className="bg-background border border-slate-800 rounded-xl p-3 text-slate-300 flex flex-wrap gap-1.5">
                                                {kdpMetadata.search_keywords.map((kw, i) => (
                                                    <span key={i} className="bg-slate-800 text-[10px] px-2 py-0.5 rounded-md text-slate-300">
                                                        {kw}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                        
                                        <div className="space-y-1">
                                            <span className="text-[10px] uppercase font-mono text-slate-500 font-semibold block">BISAC-Kategorien:</span>
                                            <div className="bg-background border border-slate-800 rounded-xl p-3 text-slate-300 space-y-1">
                                                {kdpMetadata.recommended_bisac_categories.map((c, i) => (
                                                    <div key={i} className="text-[10px] truncate">&bull; {c}</div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="bg-background p-3.5 rounded-2xl border border-slate-800 flex justify-between items-center">
                                        <div className="space-y-0.5">
                                            <span className="text-[10px] uppercase font-mono text-slate-500 font-semibold">Preis-Empfehlung:</span>
                                            <div className="text-sm font-bold text-white">{kdpMetadata.pricing_recommendation.price}</div>
                                        </div>
                                        <div className="text-[10px] text-slate-400 text-right max-w-xs leading-normal">
                                            {kdpMetadata.pricing_recommendation.reason}
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div className="text-center py-10 text-slate-600 text-xs space-y-1">
                                    <Clipboard className="w-6 h-6 mx-auto text-slate-700" />
                                    <p>Keine Metadaten generiert. Klicke auf 'Metadaten erstellen' zur Analyse.</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

import { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import type { 
    BookProjectDetail, 
    LektoratFinding, 
    KdpMetadata,
    GlobalLektoratFinding
} from '../lib/api';
import { formatAuthorStyles } from '../lib/authors';
import { 
    updateProBook, 
    suggestProCharacters,
    generateProOutline, 
    improveProChapterOutline,
    updateProOutline,
    generateProChapter, 
    updateProChapter,
    proofreadProChapter, 
    proofreadProBookGlobally,
    generateProCover,
    getProCoverUrl, 
    getProEpubUrl,
    fetchProKdpMetadata,
    cancelProBookGeneration,
    suggestProStyleRefinement,
    suggestProCoverPrompt,
    suggestProEpubMetadata
} from '../lib/api';
import { 
    ArrowLeft, 
    Save, 
    Sparkles, 
    BookOpen, 
    Clipboard, 
    Download, 
    Check, 
    Loader2, 
    AlertTriangle,
    CheckCircle,
    Maximize2,
    Plus,
    Trash2
} from 'lucide-react';
import toast from 'react-hot-toast';

interface BookEditorProps {
    project: BookProjectDetail;
    onBack: () => void;
}

type StepType = 'concept' | 'outline' | 'writing' | 'lektorat' | 'export';

const TEXT_MODELS = [
    { value: 'gemini-3.5-flash', label: 'Gemini 3.5 Flash (Neueste Generation)' },
    { value: 'gemini-3.1-flash-lite', label: 'Gemini 3.1 Flash (Effizient & Schnell)' },
    { value: 'gemini-3.1-pro-preview', label: 'Gemini 3.1 Pro (Meisterhafte Lyrik)' },
    { value: 'deepseek-v4-flash', label: 'DeepSeek V4 Flash (Neu & Schnell)' },
    { value: 'deepseek-v4-pro', label: 'DeepSeek V4 Pro (High-End Reasoning)' },
];

const IMAGE_MODELS = [
    { value: 'gemini-3.1-flash-image-preview', label: 'Gemini 3.1 Flash (512px - Günstig)' },
    { value: 'gemini-3-pro-image-preview', label: 'Gemini 3.0 Pro (Premium Qualität)' },
    { value: 'fal-ai/flux/schnell', label: 'Flux/schnell (fal.ai)' }
];

export default function BookEditor({ project, onBack }: BookEditorProps) {
    const { loadProProjectDetail, currentProProject } = useStore();
    const activeProject = currentProProject || project;

    const [activeStep, setActiveStep] = useState<StepType>('concept');
    const [isSaving, setIsSaving] = useState(false);
    const [isAiLoading, setIsAiLoading] = useState(false);

    // Step 1 State: Concept & Characters
    const [charBible, setCharBible] = useState(activeProject.characters_bible || '');
    const [charModel, setCharModel] = useState('gemini-3.1-flash-lite');
    const [styleBible, setStyleBible] = useState(activeProject.style_bible || '');
    const [styleModel, setStyleModel] = useState('gemini-3.1-flash-lite');
    const [activeConceptTab, setActiveConceptTab] = useState<'characters' | 'style'>('characters');

    // Step 2 State: Outline
    const [numChapters, setNumChapters] = useState(activeProject.chapters.length || 8);
    const [outlineModel, setOutlineModel] = useState('gemini-3.1-flash-lite');
    const [editableChapters, setEditableChapters] = useState<any[]>([]);
    const [outlineFeedback, setOutlineFeedback] = useState('');
    const [chapterFeedbacks, setChapterFeedbacks] = useState<{ [key: number]: string }>({});

    // Step 3 State: Writing
    const [selectedChapterNum, setSelectedChapterNum] = useState<number>(1);
    const [writingModel, setWritingModel] = useState('deepseek-v4-pro');
    const [chapterText, setChapterText] = useState('');
    const [chapterTitle, setChapterTitle] = useState('');
    const [chapterOutline, setChapterOutline] = useState('');
    const [feedback, setFeedback] = useState('');
    const [targetWords, setTargetWords] = useState<number>(2000);

    // Step 4 State: Lektorat
    const [lektoratTab, setLektoratTab] = useState<'chapter' | 'global'>('chapter');
    const [lektoratModel, setLektoratModel] = useState('gemini-3.5-flash');
    const [globalLektoratModel, setGlobalLektoratModel] = useState('gemini-3.5-flash');
    const [findings, setFindings] = useState<LektoratFinding[]>([]);
    const [globalFindings, setGlobalFindings] = useState<GlobalLektoratFinding[]>([]);

    // Step 5 State: Export & Cover
    const [coverPrompt, setCoverPrompt] = useState(activeProject.cover_prompt || '');
    const [coverPromptModel, setCoverPromptModel] = useState('gemini-3.1-flash-lite');
    const [coverImageModel, setCoverImageModel] = useState('fal-ai/flux/schnell');
    const [coverVersion, setCoverVersion] = useState(Date.now().toString());
    const [kdpMetadata, setKdpMetadata] = useState<KdpMetadata | null>(null);
    const [kdpModel, setKdpModel] = useState('gemini-3.1-flash-lite');

    // Step 5 State: EPUB Metadata
    const [epubTab, setEpubTab] = useState<'cover' | 'metadata' | 'export'>('cover');
    const [epubAuthor, setEpubAuthor] = useState(activeProject.epub_author || '');
    const [epubDedication, setEpubDedication] = useState(activeProject.epub_dedication || '');
    const [epubAfterword, setEpubAfterword] = useState(activeProject.epub_afterword || '');
    const [epubImprint, setEpubImprint] = useState(activeProject.epub_imprint || '');
    const [epubMetaModel, setEpubMetaModel] = useState('gemini-3.1-flash-lite');

    // Reload active project context when step changes to keep it fresh
    useEffect(() => {
        loadProProjectDetail(activeProject.id);
    }, [activeStep, loadProProjectDetail, activeProject.id]);

    // Synchronize editable chapters for outline editing
    useEffect(() => {
        if (activeProject.outline) {
            try {
                const data = JSON.parse(activeProject.outline);
                const list = data.chapters || [];
                const merged = list.map((c: any) => {
                    const dbChap = activeProject.chapters.find((dc: any) => dc.chapter_number === c.chapter_number);
                    return {
                        id: dbChap?.id,
                        chapter_number: c.chapter_number,
                        title: c.title || dbChap?.title || '',
                        plot_outline: c.plot_outline || dbChap?.plot_outline || ''
                    };
                });
                setEditableChapters(merged);
            } catch (e) {
                // Fallback
                setEditableChapters(activeProject.chapters.map(c => ({
                    id: c.id,
                    chapter_number: c.chapter_number,
                    title: c.title,
                    plot_outline: c.plot_outline
                })));
            }
        } else {
            setEditableChapters(activeProject.chapters.map(c => ({
                id: c.id,
                chapter_number: c.chapter_number,
                title: c.title,
                plot_outline: c.plot_outline
            })));
        }
    }, [activeProject]);

    // Sync character bible, style bible, cover prompt and epub metadata when project details load
    useEffect(() => {
        setCharBible(activeProject.characters_bible || '');
        setStyleBible(activeProject.style_bible || '');
        setCoverPrompt(activeProject.cover_prompt || '');
        setEpubAuthor(activeProject.epub_author || '');
        setEpubDedication(activeProject.epub_dedication || '');
        setEpubAfterword(activeProject.epub_afterword || '');
        setEpubImprint(activeProject.epub_imprint || '');
    }, [activeProject.id, activeProject.characters_bible, activeProject.style_bible, activeProject.cover_prompt,
        activeProject.epub_author, activeProject.epub_dedication, activeProject.epub_afterword, activeProject.epub_imprint]);

    const dbChapter = activeProject.chapters.find(c => c.chapter_number === selectedChapterNum);

    // Sync selected chapter content when selected chapter changes
    useEffect(() => {
        if (dbChapter) {
            setChapterText(dbChapter.content || '');
            setChapterTitle(dbChapter.title || '');
            setChapterOutline(dbChapter.plot_outline || '');
            
            // Calculate a default suggestion for target words based on outline length
            const outlineLen = (dbChapter.plot_outline || '').trim().length;
            let suggestion = 2000;
            if (outlineLen > 0) {
                if (outlineLen < 150) {
                    suggestion = 1200;
                } else if (outlineLen < 350) {
                    suggestion = 1800;
                } else {
                    suggestion = 2500;
                }
            }
            setTargetWords(suggestion);
        } else {
            setChapterText('');
            setChapterTitle('');
            setChapterOutline('');
            setTargetWords(2000);
        }
        setFindings([]); // Clear proofread findings when switching chapters
    }, [selectedChapterNum, dbChapter?.id, dbChapter?.status]);

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

    const handleSaveStyle = async () => {
        setIsSaving(true);
        try {
            await updateProBook(activeProject.id, { style_bible: styleBible });
            toast.success('Stil-Bible gespeichert!');
        } catch (e: any) {
            toast.error('Fehler beim Speichern: ' + e.message);
        } finally {
            setIsSaving(false);
        }
    };

    const handleSuggestStyle = async () => {
        setIsAiLoading(true);
        try {
            toast.loading('Generiere Stil-Verfeinerung...', { id: 'ai' });
            const res = await suggestProStyleRefinement(activeProject.id, styleModel);
            setStyleBible(res.suggested_style);
            toast.success('Stil erfolgreich verfeinert!', { id: 'ai' });
        } catch (e: any) {
            toast.error('Fehler: ' + e.message, { id: 'ai' });
        } finally {
            setIsAiLoading(false);
        }
    };


    // --- Step 2 Actions ---

    const handleGenerateOutline = async (useFeedback: boolean = false) => {
        setIsAiLoading(true);
        try {
            toast.loading('Gliederung wird erstellt...', { id: 'ai' });
            await generateProOutline(activeProject.id, numChapters, outlineModel, useFeedback ? outlineFeedback : undefined);
            toast.success('Outline erfolgreich erstellt!', { id: 'ai' });
            if (useFeedback) setOutlineFeedback('');
            await loadProProjectDetail(activeProject.id);
        } catch (e: any) {
            toast.error('Fehler: ' + e.message, { id: 'ai' });
        } finally {
            setIsAiLoading(false);
        }
    };

    const handleImproveChapterOutline = async (num: number) => {
        const instr = chapterFeedbacks[num] || '';
        if (!instr.trim()) {
            toast.error('Bitte gib erst eine Verbesserungsanweisung für dieses Kapitel ein.');
            return;
        }
        setIsAiLoading(true);
        try {
            toast.loading(`Kapitel ${num} Gliederung wird überarbeitet...`, { id: 'ai' });
            await improveProChapterOutline(activeProject.id, num, outlineModel, instr);
            toast.success(`Kapitel ${num} erfolgreich überarbeitet!`, { id: 'ai' });
            setChapterFeedbacks(prev => ({ ...prev, [num]: '' }));
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

    const updateEditableChapterField = (index: number, field: string, value: string) => {
        setEditableChapters(prev => prev.map((c, i) => 
            i === index ? { ...c, [field]: value } : c
        ));
    };

    const reindexChapters = (chapters: any[]) => {
        return chapters.map((c, idx) => ({
            ...c,
            chapter_number: idx + 1
        }));
    };

    const handleInsertChapter = (index: number) => {
        const newChap = {
            title: `Neues Kapitel`,
            plot_outline: '',
        };
        const newChapters = [...editableChapters];
        newChapters.splice(index, 0, newChap);
        const reindexed = reindexChapters(newChapters);
        setEditableChapters(reindexed);
        setNumChapters(reindexed.length);
    };

    const handleDeleteChapter = (index: number) => {
        if (editableChapters.length <= 1) {
            toast.error('Ein Buch muss mindestens ein Kapitel haben.');
            return;
        }
        if (!window.confirm('Möchtest du dieses Kapitel wirklich aus der Gliederung entfernen?')) return;
        
        const newChapters = [...editableChapters];
        newChapters.splice(index, 1);
        const reindexed = reindexChapters(newChapters);
        setEditableChapters(reindexed);
        setNumChapters(reindexed.length);
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
                useFeedback ? feedback : undefined,
                targetWords
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

    const handleCancelGeneration = async () => {
        setIsSaving(true);
        try {
            await cancelProBookGeneration(activeProject.id);
            toast.success('Generierung abgebrochen!');
            await loadProProjectDetail(activeProject.id);
        } catch (e: any) {
            toast.error('Fehler beim Abbrechen: ' + e.message);
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

        try {
            toast.loading('Korrektur wird direkt gespeichert...', { id: 'lektorat-save' });
            await updateProChapter(activeProject.id, selectedChapterNum, {
                title: chapterTitle,
                plot_outline: chapterOutline,
                content: newText
            });
            await loadProProjectDetail(activeProject.id);
            toast.success('Korrektur angewendet und gespeichert!', { id: 'lektorat-save' });
        } catch (e: any) {
            toast.error('Fehler beim Speichern: ' + e.message, { id: 'lektorat-save' });
        }
    };

    const handleRunGlobalLektorat = async () => {
        setIsAiLoading(true);
        try {
            toast.loading('Globales Lektorat läuft über das gesamte Manuskript...', { id: 'ai' });
            const res = await proofreadProBookGlobally(activeProject.id, globalLektoratModel);
            setGlobalFindings(res.findings);
            if (res.findings.length === 0) {
                toast.success('Keine globalen Widersprüche oder Probleme gefunden!', { id: 'ai' });
            } else {
                toast.success(`${res.findings.length} globale Befunde gefunden!`, { id: 'ai' });
            }
        } catch (e: any) {
            toast.error('Fehler beim globalen Lektorat: ' + e.message, { id: 'ai' });
        } finally {
            setIsAiLoading(false);
        }
    };


    // --- Step 5 Actions ---

    const handleSuggestCoverPrompt = async () => {
        setIsAiLoading(true);
        try {
            toast.loading('Generiere Cover-Vorschlag...', { id: 'ai' });
            const res = await suggestProCoverPrompt(activeProject.id, coverPromptModel);
            setCoverPrompt(res.suggested_prompt);
            toast.success('Cover-Prompt erfolgreich generiert!', { id: 'ai' });
        } catch (e: any) {
            toast.error('Fehler: ' + e.message, { id: 'ai' });
        } finally {
            setIsAiLoading(false);
        }
    };

    const handleSaveCoverPrompt = async () => {
        setIsSaving(true);
        try {
            await updateProBook(activeProject.id, { cover_prompt: coverPrompt });
            toast.success('Cover-Prompt gespeichert!');
            await loadProProjectDetail(activeProject.id);
        } catch (e: any) {
            toast.error('Fehler beim Speichern: ' + e.message);
        } finally {
            setIsSaving(false);
        }
    };

    const handleSuggestEpubMetadata = async () => {
        setIsAiLoading(true);
        try {
            toast.loading('Generiere EPUB-Metadaten...', { id: 'ai' });
            const res = await suggestProEpubMetadata(activeProject.id, epubMetaModel);
            if (res.epub_author) setEpubAuthor(res.epub_author);
            if (res.epub_dedication) setEpubDedication(res.epub_dedication);
            if (res.epub_afterword) setEpubAfterword(res.epub_afterword);
            if (res.epub_imprint) setEpubImprint(res.epub_imprint);
            toast.success('EPUB-Metadaten generiert!', { id: 'ai' });
        } catch (e: any) {
            toast.error('Fehler: ' + e.message, { id: 'ai' });
        } finally {
            setIsAiLoading(false);
        }
    };

    const handleSaveEpubMetadata = async () => {
        setIsSaving(true);
        try {
            await updateProBook(activeProject.id, {
                epub_author: epubAuthor,
                epub_dedication: epubDedication,
                epub_afterword: epubAfterword,
                epub_imprint: epubImprint,
            });
            toast.success('EPUB-Metadaten gespeichert!');
            await loadProProjectDetail(activeProject.id);
        } catch (e: any) {
            toast.error('Fehler beim Speichern: ' + e.message);
        } finally {
            setIsSaving(false);
        }
    };

    const handleGenerateCover = async () => {
        if (!coverPrompt.trim()) {
            toast.error('Bitte beschreibe erst ein Motiv für das Cover.');
            return;
        }
        setIsAiLoading(true);
        try {
            toast.loading('Cover-Erstellung läuft im Hintergrund...', { id: 'ai' });
            await generateProCover(activeProject.id, coverPrompt, coverImageModel);
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
                    <div className="bg-surface/50 px-4 py-3 rounded-2xl border border-slate-800/80 flex items-center gap-4 w-full sm:w-auto justify-between sm:justify-start">
                        <div className="flex items-center gap-3">
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
                        <button
                            onClick={handleCancelGeneration}
                            className="text-[10px] uppercase font-mono tracking-wider bg-red-500/10 hover:bg-red-500/20 text-red-400 px-3 py-1.5 rounded-lg border border-red-500/20 font-bold transition-colors"
                        >
                            Abbrechen
                        </button>
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
                                    <span className="text-slate-300 font-medium">{formatAuthorStyles(activeProject.style)}</span>
                                </div>
                                <div>
                                    <span className="text-slate-500 block uppercase font-mono text-[9px]">Buchidee</span>
                                    <p className="text-slate-400 leading-relaxed mt-0.5">{activeProject.prompt}</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="lg:col-span-2 bg-surface p-5 rounded-3xl border border-slate-800 flex flex-col space-y-4">
                        {/* Tab-Header */}
                        <div className="flex border-b border-slate-800/80 pb-2.5 gap-4 shrink-0">
                            <button 
                                onClick={() => setActiveConceptTab('characters')}
                                className={`pb-2 text-xs font-bold transition-all relative ${
                                    activeConceptTab === 'characters' 
                                    ? 'text-white after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:bg-primary' 
                                    : 'text-slate-400 hover:text-slate-200'
                                }`}
                            >
                                Charakter-Bible
                            </button>
                            <button 
                                onClick={() => setActiveConceptTab('style')}
                                className={`pb-2 text-xs font-bold transition-all relative ${
                                    activeConceptTab === 'style' 
                                    ? 'text-white after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:bg-primary' 
                                    : 'text-slate-400 hover:text-slate-200'
                                }`}
                            >
                                Stil-Bible (Schreibstil)
                            </button>
                        </div>

                        {/* TAB 1: CHARACTERS */}
                        {activeConceptTab === 'characters' && (
                            <div className="flex-1 flex flex-col space-y-4">
                                <div className="flex justify-between items-center shrink-0">
                                    <span className="text-[10px] text-slate-500 font-semibold uppercase font-mono">Figuren & Beziehungen</span>
                                    
                                    <div className="flex items-center gap-2">
                                        <select 
                                            value={charModel}
                                            onChange={(e) => setCharModel(e.target.value)}
                                            className="bg-background border border-slate-800 text-[10px] text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
                                        >
                                            {TEXT_MODELS.map(m => (
                                                <option key={m.value} value={m.value}>{m.label}</option>
                                            ))}
                                        </select>
                                        <button 
                                            onClick={handleSuggestCharacters}
                                            disabled={isAiLoading}
                                            className="text-[10px] bg-slate-800 hover:bg-slate-700 text-primary border border-slate-700/50 rounded-lg px-3 py-1 flex items-center gap-1 transition-colors"
                                        >
                                            <Sparkles className="w-3.5 h-3.5" />
                                            KI-Vorschlag
                                        </button>
                                    </div>
                                </div>

                                <textarea 
                                    value={charBible}
                                    onChange={(e) => setCharBible(e.target.value)}
                                    rows={12}
                                    className="w-full flex-1 bg-background border border-slate-800 rounded-2xl px-4 py-3 text-xs text-white focus:outline-none focus:border-primary font-mono leading-relaxed resize-y min-h-[300px]"
                                    placeholder="Definiere die Charaktere für dein Buch. Du kannst manuell schreiben oder den KI-Vorschlag nutzen, um Figuren und ihre Beziehungen festzuhalten..."
                                />

                                <div className="flex justify-end pt-1 shrink-0">
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
                        )}

                        {/* TAB 2: STYLE BIBLE */}
                        {activeConceptTab === 'style' && (
                            <div className="flex-1 flex flex-col space-y-4">
                                <div className="flex justify-between items-center shrink-0">
                                    <span className="text-[10px] text-slate-500 font-semibold uppercase font-mono">Schreibregeln & Tonalität</span>
                                    
                                    <div className="flex items-center gap-2">
                                        <select 
                                            value={styleModel}
                                            onChange={(e) => setStyleModel(e.target.value)}
                                            className="bg-background border border-slate-800 text-[10px] text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
                                        >
                                            {TEXT_MODELS.map(m => (
                                                <option key={m.value} value={m.value}>{m.label}</option>
                                            ))}
                                        </select>
                                        <button 
                                            onClick={handleSuggestStyle}
                                            disabled={isAiLoading}
                                            className="text-[10px] bg-slate-800 hover:bg-slate-700 text-primary border border-slate-700/50 rounded-lg px-3 py-1 flex items-center gap-1 transition-colors"
                                        >
                                            <Sparkles className="w-3.5 h-3.5" />
                                            Stil verfeinern
                                        </button>
                                    </div>
                                </div>

                                <textarea 
                                    value={styleBible}
                                    onChange={(e) => setStyleBible(e.target.value)}
                                    rows={12}
                                    className="w-full flex-1 bg-background border border-slate-800 rounded-2xl px-4 py-3 text-xs text-white focus:outline-none focus:border-primary font-mono leading-relaxed resize-y min-h-[300px]"
                                    placeholder="Definiere die Stil-Vorgaben für das Buch. Diese wurden mit dem Autorenmix initialisiert, können aber beliebig angepasst und verfeinert werden..."
                                />

                                <div className="flex justify-end pt-1 shrink-0">
                                    <button 
                                        onClick={handleSaveStyle}
                                        disabled={isSaving}
                                        className="btn-primary py-2 px-5 text-xs flex items-center gap-1.5 rounded-xl"
                                    >
                                        {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                                        Stil-Bible speichern
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
            {/* STEP 2: OUTLINE EDITOR */}
            {activeStep === 'outline' && (
                <div className="bg-surface p-5 rounded-3xl border border-slate-800 space-y-5">
                    <div className="flex flex-col xl:flex-row justify-between xl:items-center gap-4 border-b border-slate-800/80 pb-4">
                        <div className="space-y-1">
                            <h3 className="font-semibold text-white text-sm">Buchgliederung & Kapitel</h3>
                            <p className="text-xs text-text-muted">Plane und verfeinere den Handlungsstrang deines Buches vor dem Schreiben.</p>
                        </div>

                        <div className="flex items-center gap-3 flex-wrap">
                            {editableChapters.length > 0 && (
                                <button 
                                    onClick={handleSaveOutline}
                                    disabled={isSaving}
                                    className="bg-slate-800 hover:bg-slate-700 text-white border border-slate-705 py-1.5 px-4 text-xs flex items-center gap-1.5 rounded-xl transition-all"
                                >
                                    {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                                    Gliederung speichern
                                </button>
                            )}

                            <div className="flex items-center gap-2">
                                <label className="text-xs text-slate-400">Kapitel:</label>
                                <select 
                                    value={numChapters} 
                                    onChange={(e) => setNumChapters(parseInt(e.target.value))}
                                    className="bg-background border border-slate-800 text-xs text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
                                >
                                    {Array.from(new Set([3, 4, 5, 6, 7, 8, 9, 10, 12, numChapters])).sort((a, b) => a - b).map(n => (
                                        <option key={n} value={n}>{n} Kapitel</option>
                                    ))}
                                </select>
                                <select 
                                    value={outlineModel} 
                                    onChange={(e) => setOutlineModel(e.target.value)}
                                    className="bg-background border border-slate-800 text-xs text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
                                >
                                    {TEXT_MODELS.map(m => (
                                        <option key={m.value} value={m.value}>{m.label}</option>
                                    ))}
                                </select>
                                <button 
                                    onClick={() => handleGenerateOutline(!!outlineFeedback.trim())}
                                    disabled={isAiLoading}
                                    className="btn-primary py-1.5 px-4 text-xs flex items-center gap-1 rounded-xl shrink-0"
                                >
                                    <Sparkles className="w-3.5 h-3.5" />
                                    {editableChapters.length === 0 ? 'Gliederung generieren' : 'Komplett neu generieren'}
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Feedback box for full outline regeneration */}
                    <div className="bg-background/40 p-3 rounded-2xl border border-slate-800 flex gap-2 items-center text-xs">
                        <span className="text-slate-500 font-mono text-[10px] uppercase font-bold shrink-0">KI-Feedback:</span>
                        <input
                            type="text"
                            value={outlineFeedback}
                            onChange={(e) => setOutlineFeedback(e.target.value)}
                            placeholder="Anweisung für die gesamte Gliederung (z.B. 'Mach die Story düsterer' oder 'Füge ein Happy End hinzu')"
                            className="bg-transparent border-none text-xs text-white placeholder-slate-600 focus:outline-none w-full"
                        />
                        {outlineFeedback && (
                            <button
                                onClick={() => setOutlineFeedback('')}
                                className="text-slate-500 hover:text-white shrink-0 text-xs"
                            >
                                Zurücksetzen
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
                        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-2 custom-scrollbar">
                            {editableChapters.map((chap, i) => (
                                <div key={i} className="bg-background p-4 rounded-2xl border border-slate-800 space-y-3 animate-fadeIn">
                                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800 pb-2">
                                        <div className="flex items-center gap-3 flex-1">
                                            <span className="w-6 h-6 rounded-lg bg-slate-800 flex items-center justify-center font-mono text-xs text-slate-300 shrink-0 font-bold">
                                                {chap.chapter_number}
                                            </span>
                                            <input 
                                                type="text" 
                                                value={chap.title}
                                                onChange={(e) => updateEditableChapterField(i, 'title', e.target.value)}
                                                className="bg-surface border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-primary w-full max-w-sm"
                                                placeholder="Kapiteltitel"
                                            />
                                        </div>
                                        
                                        <div className="flex items-center gap-2">
                                            <button
                                                type="button"
                                                onClick={() => handleInsertChapter(i)}
                                                className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition-colors border border-slate-700/50 text-[10px] flex items-center gap-1 font-medium"
                                                title="Kapitel davor einfügen"
                                            >
                                                <Plus className="w-3.5 h-3.5 text-primary" />
                                                Davor einfügen
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => handleInsertChapter(i + 1)}
                                                className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition-colors border border-slate-700/50 text-[10px] flex items-center gap-1 font-medium"
                                                title="Kapitel danach einfügen"
                                            >
                                                <Plus className="w-3.5 h-3.5 text-primary" />
                                                Danach einfügen
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => handleDeleteChapter(i)}
                                                className="p-1.5 bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 rounded-lg transition-colors border border-slate-700/50"
                                                title="Kapitel löschen"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                    </div>

                                    <textarea 
                                        value={chap.plot_outline}
                                        onChange={(e) => updateEditableChapterField(i, 'plot_outline', e.target.value)}
                                        rows={6}
                                        className="w-full bg-surface border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-primary resize-y leading-relaxed"
                                        placeholder="Handlungsstrang und Ereignisse für dieses Kapitel..."
                                    />

                                    {/* Feedback for improving this single chapter's outline */}
                                    <div className="flex gap-2 items-center bg-surface p-2 rounded-xl border border-slate-800">
                                        <input
                                            type="text"
                                            value={chapterFeedbacks[chap.chapter_number] || ''}
                                            onChange={(e) => setChapterFeedbacks(prev => ({ ...prev, [chap.chapter_number]: e.target.value }))}
                                            placeholder="Kapitel-Anweisung (z.B. 'Füge Charakter Y hinzu' oder 'Mache es spannender')"
                                            className="bg-transparent border-none text-[11px] text-white placeholder-slate-600 focus:outline-none w-full px-2"
                                        />
                                        <button
                                            onClick={() => handleImproveChapterOutline(chap.chapter_number)}
                                            disabled={isAiLoading || !(chapterFeedbacks[chap.chapter_number] || '').trim()}
                                            className="bg-slate-800 hover:bg-slate-700 text-amber-400 text-[10px] px-3.5 py-1.5 rounded-lg transition-colors border border-slate-700/50 shrink-0 font-medium flex items-center gap-1"
                                        >
                                            <Sparkles className="w-3 h-3" />
                                            KI-Verbessern
                                        </button>
                                    </div>
                                </div>
                            ))}
                            
                            <div className="flex justify-center pt-2">
                                <button
                                    type="button"
                                    onClick={() => handleInsertChapter(editableChapters.length)}
                                    className="py-2.5 px-6 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 rounded-xl transition-all text-xs flex items-center gap-2"
                                >
                                    <Plus className="w-4 h-4 text-primary" />
                                    Neues Kapitel am Ende anfügen
                                </button>
                            </div>
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
                                <div className="flex items-center gap-1.5 bg-background border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-300">
                                    <span>Zielwörter:</span>
                                    <input 
                                        type="number" 
                                        value={targetWords} 
                                        onChange={(e) => setTargetWords(parseInt(e.target.value) || 2000)}
                                        className="w-14 bg-transparent text-white font-bold outline-none text-right"
                                        step={100}
                                        min={200}
                                    />
                                </div>
                                <select 
                                    value={writingModel}
                                    onChange={(e) => setWritingModel(e.target.value)}
                                    className="bg-background border border-slate-800 text-xs text-slate-300 rounded-lg px-2 py-1.5 focus:outline-none"
                                >
                                    {TEXT_MODELS.map(m => (
                                        <option key={m.value} value={m.value}>{m.label}</option>
                                    ))}
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
                <div className="space-y-6">
                    {/* Sub-tab selection */}
                    <div className="flex border-b border-slate-800/80 pb-2.5 gap-4">
                        <button 
                            onClick={() => setLektoratTab('chapter')}
                            className={`pb-2 text-xs font-bold transition-all relative ${
                                lektoratTab === 'chapter' 
                                ? 'text-white after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:bg-primary' 
                                : 'text-slate-400 hover:text-slate-200'
                            }`}
                        >
                            Kapitel-Lektorat (Einzelprüfung)
                        </button>
                        <button 
                            onClick={() => setLektoratTab('global')}
                            className={`pb-2 text-xs font-bold transition-all relative ${
                                lektoratTab === 'global' 
                                ? 'text-white after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:bg-primary' 
                                : 'text-slate-400 hover:text-slate-200'
                            }`}
                        >
                            Globales Lektorat (Gesamtes Werk)
                        </button>
                    </div>

                    {lektoratTab === 'chapter' ? (
                        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 animate-fadeIn">
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
                                            {TEXT_MODELS.map(m => (
                                                <option key={m.value} value={m.value}>{m.label}</option>
                                            ))}
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
                                    <div className="bg-background p-3 rounded-2xl border border-slate-800 space-y-2">
                                        <div className="flex justify-between items-center">
                                            <h4 className="text-xs font-semibold text-slate-400">Geladener Kapiteltext (Vorschau):</h4>
                                            {chapterText !== (dbChapter?.content || '') && (
                                                <button
                                                    onClick={handleSaveChapterContent}
                                                    disabled={isSaving}
                                                    className="bg-slate-800 hover:bg-slate-700 text-white border border-slate-705 py-1.5 px-3 rounded-xl flex items-center gap-1.5 transition-all text-[10px] font-medium"
                                                >
                                                    {isSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                                                    Änderungen speichern
                                                </button>
                                            )}
                                        </div>
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
                                                <div key={idx} className="bg-background p-4.5 rounded-2xl border border-slate-800 space-y-3 text-xs animate-fadeIn">
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
                    ) : (
                        <div className="bg-surface p-5 rounded-3xl border border-slate-800 space-y-5 animate-fadeIn">
                            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 border-b border-slate-800 pb-3">
                                <div className="space-y-1">
                                    <h3 className="font-semibold text-white text-sm">
                                        Globales Lektorat (Gesamtes Werk)
                                    </h3>
                                    <p className="text-xs text-text-muted">Analysiert das gesamte Manuskript auf Logikfehler, Stilbrüche und Charakterkonsistenz.</p>
                                </div>

                                <div className="flex items-center gap-2">
                                    <select 
                                        value={globalLektoratModel}
                                        onChange={(e) => setGlobalLektoratModel(e.target.value)}
                                        className="bg-background border border-slate-800 text-xs text-slate-300 rounded-lg px-2 py-1.5 focus:outline-none"
                                    >
                                        {TEXT_MODELS.map(m => (
                                            <option key={m.value} value={m.value}>{m.label}</option>
                                        ))}
                                    </select>
                                    <button 
                                        onClick={handleRunGlobalLektorat}
                                        disabled={isAiLoading}
                                        className="btn-primary py-1.5 px-4 text-xs flex items-center gap-1 rounded-xl"
                                    >
                                        <Sparkles className="w-3.5 h-3.5" />
                                        Globales Lektorat starten
                                    </button>
                                </div>
                            </div>

                            {/* Global findings display */}
                            {globalFindings.length === 0 ? (
                                <div className="text-center py-12 text-slate-500 text-xs space-y-2">
                                    <CheckCircle className="w-8 h-8 mx-auto text-slate-600" />
                                    <p>Keine ungelösten globalen Lektorat-Befunde. Starte das globale Lektorat über den Button oben.</p>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    <h4 className="text-xs font-semibold text-white flex items-center gap-2">
                                        <AlertTriangle className="w-4 h-4 text-amber-500" />
                                        Globale Befunde ({globalFindings.length})
                                    </h4>

                                    <div className="space-y-3 max-h-[50vh] overflow-y-auto pr-1 custom-scrollbar">
                                        {globalFindings.map((gf, idx) => (
                                            <div key={idx} className="bg-background p-4.5 rounded-2xl border border-slate-800 space-y-3 text-xs animate-fadeIn">
                                                <div className="flex justify-between items-start gap-3">
                                                    <div className="flex items-center gap-2 flex-wrap">
                                                        <span className={`px-2 py-0.5 rounded-md font-mono text-[9px] uppercase tracking-wider font-bold ${
                                                            gf.category === 'consistency' 
                                                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' 
                                                            : gf.category === 'style'
                                                            ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                                            : 'bg-red-500/10 text-red-400 border border-red-500/20'
                                                        }`}>
                                                            {gf.category}
                                                        </span>
                                                        <span className="text-[10px] text-slate-400 font-semibold">
                                                            Kapitel: {gf.chapters_involved.join(', ') || 'Alle'}
                                                        </span>
                                                    </div>
                                                    <span className="text-[10px] text-slate-500 font-semibold">Globaler Befund</span>
                                                </div>

                                                <div className="text-slate-300 font-semibold font-sans">
                                                    {gf.description}
                                                </div>

                                                <div className="bg-primary/5 p-3 rounded-xl border border-primary/10 space-y-1">
                                                    <span className="text-[9px] font-mono uppercase text-primary font-bold">Lösungsvorschlag:</span>
                                                    <p className="text-[11px] text-slate-300 font-serif leading-relaxed italic">{gf.suggested_fix}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                    
                                    <div className="bg-slate-800/40 p-3.5 rounded-2xl border border-slate-800 flex items-start gap-3">
                                        <AlertTriangle className="w-5 h-5 text-primary shrink-0 mt-0.5" />
                                        <p className="text-[10px] text-slate-400 leading-normal">
                                            <b>Hinweis:</b> Globale Befunde betreffen oft mehrere Kapitel oder die Struktur des Buchs. 
                                            Nutze diese Liste als Arbeitszettel, um im Tab <b>"3. Kapitel schreiben"</b> die jeweiligen 
                                            Kapiteltexte gezielt manuell zu editieren oder mit Feedback neu zu generieren.
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* STEP 5: COVER & EXPORT */}
            {activeStep === 'export' && (
                <div className="space-y-5">
                    {/* Sub-tab nav */}
                    <div className="flex border-b border-slate-800/80 pb-2.5 gap-5">
                        {[
                            { id: 'cover', label: 'Cover-Erstellung' },
                            { id: 'metadata', label: 'Buch-Metadaten (EPUB)' },
                            { id: 'export', label: 'Export & KDP' },
                        ].map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setEpubTab(tab.id as any)}
                                className={`pb-2 text-xs font-bold transition-all relative ${
                                    epubTab === tab.id
                                    ? 'text-white after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:bg-primary'
                                    : 'text-slate-400 hover:text-slate-200'
                                }`}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </div>
                    {/* ===== TAB: COVER ===== */}
                    {epubTab === 'cover' && (
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fadeIn">
                            {/* Cover Generator Panel */}
                            <div className="lg:col-span-1 bg-surface p-5 rounded-3xl border border-slate-800 space-y-4">
                                <h3 className="font-semibold text-white text-sm">Cover-Erstellung (KDP-Format)</h3>
                        
                                {activeProject.cover_image_url ? (
                                    <div className="space-y-3">
                                    <div className="aspect-[2/3] w-full bg-background rounded-2xl border border-slate-800 overflow-hidden shadow-inner flex items-center justify-center relative group">
                                        <img 
                                            src={getProCoverUrl(activeProject.id, coverVersion)}
                                            alt="Buch Cover"
                                            className="w-full h-full object-cover"
                                        />
                                        <div className="absolute inset-0 bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                                            <a 
                                                href={getProCoverUrl(activeProject.id, coverVersion)}
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
                            <div className="flex justify-between items-center">
                                <label className="text-xs font-semibold text-slate-300">Bild-Prompt (Editierbar):</label>
                                
                                <div className="flex items-center gap-2">
                                    <select 
                                        value={coverPromptModel}
                                        onChange={(e) => setCoverPromptModel(e.target.value)}
                                        className="bg-background border border-slate-800 text-[10px] text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
                                    >
                                        {TEXT_MODELS.map(m => (
                                            <option key={m.value} value={m.value}>{m.label}</option>
                                        ))}
                                    </select>
                                    <button 
                                        onClick={handleSuggestCoverPrompt}
                                        disabled={isAiLoading || activeProject.status === 'generating'}
                                        className="text-[10px] bg-slate-800 hover:bg-slate-700 text-primary border border-slate-700/50 rounded-lg px-2.5 py-1 flex items-center gap-1 transition-colors"
                                    >
                                        <Sparkles className="w-3 h-3" />
                                        KI-Vorschlag
                                    </button>
                                </div>
                            </div>
                            <textarea 
                                value={coverPrompt}
                                onChange={(e) => setCoverPrompt(e.target.value)}
                                rows={4}
                                className="w-full bg-background border border-slate-800 rounded-2xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-primary resize-none font-serif leading-relaxed"
                                placeholder="z. B. Ein mystischer Wald im Mondlicht, Ölgemälde, weiches Licht, hoher Kontrast..."
                            />
                            <div className="flex justify-end mt-1">
                                <button 
                                    onClick={handleSaveCoverPrompt}
                                    disabled={isSaving}
                                    className="bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-[10px] px-3 py-1.5 rounded-lg transition-colors border border-slate-700/50 flex items-center gap-1"
                                >
                                    {isSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                                    Prompt speichern
                                </button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-slate-300">Bild API / Modell:</label>
                            <select 
                                value={coverImageModel}
                                onChange={(e) => setCoverImageModel(e.target.value)}
                                className="w-full bg-background border border-slate-800 text-xs text-slate-300 rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary"
                            >
                                {IMAGE_MODELS.map(m => (
                                    <option key={m.value} value={m.value}>{m.label}</option>
                                ))}
                            </select>
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
                        </div>
                    )}

                    {/* ===== TAB: EPUB METADATEN ===== */}
                    {epubTab === 'metadata' && (
                        <div className="bg-surface p-5 rounded-3xl border border-slate-800 space-y-5 animate-fadeIn">
                            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 border-b border-slate-800/80 pb-3">
                                <div className="space-y-1">
                                    <h3 className="font-semibold text-white text-sm">Buch-Metadaten für EPUB</h3>
                                    <p className="text-xs text-text-muted">Diese Texte erscheinen im EPUB als Titelblatt, Widmung, Impressum und Nachwort.</p>
                                </div>
                                <div className="flex items-center gap-2 shrink-0">
                                    <select
                                        value={epubMetaModel}
                                        onChange={(e) => setEpubMetaModel(e.target.value)}
                                        className="bg-background border border-slate-800 text-[10px] text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
                                    >
                                        {TEXT_MODELS.map(m => (
                                            <option key={m.value} value={m.value}>{m.label}</option>
                                        ))}
                                    </select>
                                    <button
                                        onClick={handleSuggestEpubMetadata}
                                        disabled={isAiLoading}
                                        className="bg-slate-800 hover:bg-slate-700 text-primary border border-slate-700/50 text-xs px-3 py-1.5 rounded-xl transition-colors flex items-center gap-1.5"
                                    >
                                        {isAiLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                                        KI-Vorschlag (alle Felder)
                                    </button>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                                {/* Autor */}
                                <div className="space-y-1.5">
                                    <label className="text-[10px] uppercase font-mono text-slate-500 font-semibold">Autor / Pseudonym</label>
                                    <input
                                        type="text"
                                        value={epubAuthor}
                                        onChange={(e) => setEpubAuthor(e.target.value)}
                                        className="w-full bg-background border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-primary"
                                        placeholder="z. B. Stanzwerk Pro oder ein Künstlername"
                                    />
                                </div>

                                {/* Widmung */}
                                <div className="space-y-1.5">
                                    <label className="text-[10px] uppercase font-mono text-slate-500 font-semibold">Widmung (optional)</label>
                                    <textarea
                                        value={epubDedication}
                                        onChange={(e) => setEpubDedication(e.target.value)}
                                        rows={3}
                                        className="w-full bg-background border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-primary resize-none font-serif"
                                        placeholder="Für alle, die träumen ..."
                                    />
                                </div>

                                {/* Nachwort */}
                                <div className="space-y-1.5 lg:col-span-2">
                                    <label className="text-[10px] uppercase font-mono text-slate-500 font-semibold">Nachwort / Afterword (optional)</label>
                                    <textarea
                                        value={epubAfterword}
                                        onChange={(e) => setEpubAfterword(e.target.value)}
                                        rows={5}
                                        className="w-full bg-background border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-primary resize-y leading-relaxed font-serif"
                                        placeholder="Dieses Buch entstand aus der Idee ..."
                                    />
                                </div>

                                {/* Impressum extra */}
                                <div className="space-y-1.5 lg:col-span-2">
                                    <label className="text-[10px] uppercase font-mono text-slate-500 font-semibold">Impressum-Zusatz (optional)</label>
                                    <textarea
                                        value={epubImprint}
                                        onChange={(e) => setEpubImprint(e.target.value)}
                                        rows={2}
                                        className="w-full bg-background border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-primary resize-none"
                                        placeholder="z. B. Haftungsausschluss oder Datenschutzhinweis ..."
                                    />
                                </div>
                            </div>

                            <div className="flex justify-end pt-1">
                                <button
                                    onClick={handleSaveEpubMetadata}
                                    disabled={isSaving}
                                    className="btn-primary py-2 px-5 text-xs flex items-center gap-1.5 rounded-xl"
                                >
                                    {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                                    EPUB-Metadaten speichern
                                </button>
                            </div>
                        </div>
                    )}

                    {/* ===== TAB: EXPORT & KDP ===== */}
                    {epubTab === 'export' && (
                        <div className="space-y-6 animate-fadeIn">
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
                                        {TEXT_MODELS.map(m => (
                                            <option key={m.value} value={m.value}>{m.label}</option>
                                        ))}
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
                    )}
                </div>
            )}
        </div>
    );
}

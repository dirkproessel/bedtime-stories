import React, { useState, useEffect, useMemo } from 'react';
import { useStore } from '../store/useStore';
import { 
    X, 
    Sparkles, 
    BookOpen, 
    Layers, 
    ArrowRight, 
    ArrowLeft, 
    Check, 
    Search, 
    Loader2, 
    ChevronUp, 
    ChevronDown, 
    Trash2, 
    Clock, 
    FileText, 
    Wand2
} from 'lucide-react';
import { 
    createAnthologyBook, 
    suggestAnthologyMetadata, 
    getThumbUrl, 
    type StoryMeta, 
    type BookProjectDetail,
    type AnthologyMetadataSuggestion
} from '../lib/api';
import { GENRES } from './StoryCreator';
import { AUTHORS, formatAuthorStyles } from '../lib/authors';
import { formatDuration } from '../lib/utils';
import toast from 'react-hot-toast';

interface AnthologyWizardProps {
    isOpen: boolean;
    onClose: () => void;
    onCreated: (project: BookProjectDetail) => void;
    initialStoryIds?: string[];
}

const EMPTY_ARRAY: string[] = [];

const TEXT_MODELS = [
    { value: 'gemini-3.7-flash', label: 'Gemini 3.7 Flash (Schnell & Kreativ)' },
    { value: 'gemini-3.7-pro', label: 'Gemini 3.7 Pro (Tiefgründig & Lyrisch)' },
    { value: 'gemini-3.1-flash-lite', label: 'Gemini 3.1 Flash (Effizient)' },
];

export default function AnthologyWizard({ isOpen, onClose, onCreated, initialStoryIds = EMPTY_ARRAY }: AnthologyWizardProps) {
    const { stories, loadStories, user } = useStore();

    const [step, setStep] = useState<1 | 2>(1);
    const [selectedStoryIds, setSelectedStoryIds] = useState<string[]>([]);
    
    // Filter and search
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedGenreFilter, setSelectedGenreFilter] = useState<string>('all');
    
    // Book details
    const [title, setTitle] = useState('');
    const [subtitle, setSubtitle] = useState('');
    const [author, setAuthor] = useState('');
    const [genre, setGenre] = useState('Erotik');
    const [style, setStyle] = useState('adams');
    const [language, setLanguage] = useState<'de' | 'en'>('de');
    const [selectedModel, setSelectedModel] = useState('gemini-3.7-flash');
    const [autoGenerateBlurb, setAutoGenerateBlurb] = useState(true);

    // AI suggestions preview
    const [aiSuggestion, setAiSuggestion] = useState<AnthologyMetadataSuggestion | null>(null);
    const [isSuggesting, setIsSuggesting] = useState(false);
    const [isCreating, setIsCreating] = useState(false);

    // Track modal open state to initialize only once upon opening
    useEffect(() => {
        if (!isOpen) return;

        if (stories.length === 0) {
            loadStories();
        }
        if (user?.username) {
            setAuthor(user.username);
        }
        if (initialStoryIds && initialStoryIds.length > 0) {
            setSelectedStoryIds(initialStoryIds);
        } else {
            setSelectedStoryIds([]);
        }
        setStep(1);
        setSearchQuery('');
        setSelectedGenreFilter('all');
        setAiSuggestion(null);
    }, [isOpen]);

    // Available stories
    const availableStories = useMemo(() => {
        return stories.filter(s => {
            const matchesSearch = !searchQuery.trim() || 
                s.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                (s.description && s.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
                (s.genre && s.genre.toLowerCase().includes(searchQuery.toLowerCase()));
            
            const matchesGenre = selectedGenreFilter === 'all' || s.genre === selectedGenreFilter;
            return matchesSearch && matchesGenre;
        });
    }, [stories, searchQuery, selectedGenreFilter]);

    // Unique genres present in stories
    const availableGenres = useMemo(() => {
        const set = new Set<string>();
        stories.forEach(s => {
            if (s.genre) set.add(s.genre);
        });
        return Array.from(set).sort();
    }, [stories]);

    // Selected stories in ordered array
    const orderedSelectedStories = useMemo(() => {
        return selectedStoryIds
            .map(id => stories.find(s => s.id === id))
            .filter((s): s is StoryMeta => !!s);
    }, [selectedStoryIds, stories]);

    // Statistics of selected stories
    const stats = useMemo(() => {
        let totalSeconds = 0;
        let estimatedWords = 0;
        orderedSelectedStories.forEach(s => {
            totalSeconds += (s.duration_seconds || 0);
            if (s.word_count) {
                estimatedWords += s.word_count;
            } else {
                estimatedWords += Math.round((s.duration_seconds || 300) / 60 * 150);
            }
        });
        return {
            count: orderedSelectedStories.length,
            totalSeconds,
            estimatedWords,
            estimatedPages: Math.max(1, Math.round(estimatedWords / 250))
        };
    }, [orderedSelectedStories]);

    if (!isOpen) return null;

    const handleToggleStory = (id: string) => {
        setSelectedStoryIds(prev => {
            if (prev.includes(id)) {
                return prev.filter(item => item !== id);
            } else {
                return [...prev, id];
            }
        });
    };

    const handleSelectAllFiltered = () => {
        const filteredIds = availableStories.map(s => s.id);
        setSelectedStoryIds(prev => {
            const set = new Set([...prev, ...filteredIds]);
            return Array.from(set);
        });
    };

    const handleDeselectAll = () => {
        setSelectedStoryIds([]);
    };

    const handleMoveOrder = (index: number, direction: 'up' | 'down') => {
        if (direction === 'up' && index === 0) return;
        if (direction === 'down' && index === selectedStoryIds.length - 1) return;

        const newArr = [...selectedStoryIds];
        const targetIdx = direction === 'up' ? index - 1 : index + 1;
        const temp = newArr[index];
        newArr[index] = newArr[targetIdx];
        newArr[targetIdx] = temp;
        setSelectedStoryIds(newArr);
    };

    const handleRemoveSelected = (id: string) => {
        setSelectedStoryIds(prev => prev.filter(item => item !== id));
    };

    const handleGoToStep2 = () => {
        if (selectedStoryIds.length === 0) {
            toast.error('Bitte wähle mindestens eine Geschichte für den Sammelband aus.');
            return;
        }

        // Detect dominant genre if not set
        const genreCounts: { [k: string]: number } = {};
        orderedSelectedStories.forEach(s => {
            if (s.genre) {
                genreCounts[s.genre] = (genreCounts[s.genre] || 0) + 1;
            }
        });
        let dominantGenre = 'Erotik';
        let maxCount = 0;
        Object.entries(genreCounts).forEach(([g, count]) => {
            if (count > maxCount) {
                maxCount = count;
                dominantGenre = g;
            }
        });
        setGenre(dominantGenre);

        // Pre-fill a default title if blank
        if (!title.trim()) {
            setTitle(`${selectedStoryIds.length} ${dominantGenre}-Geschichten`);
            setSubtitle(`Ein exklusiver Sammelband`);
        }

        setStep(2);
    };

    const handleSuggestAiMetadata = async () => {
        if (selectedStoryIds.length === 0) return;

        setIsSuggesting(true);
        try {
            const res = await suggestAnthologyMetadata({
                story_ids: selectedStoryIds,
                genre,
                style,
                language,
                author,
                model: selectedModel
            });
            setAiSuggestion(res);
            if (res.title) setTitle(res.title);
            if (res.subtitle) setSubtitle(res.subtitle);
            if (res.detected_genre) setGenre(res.detected_genre);
            toast.success('KI-Vorschläge für Titel, Klappentext & Cover erfolgreich generiert!');
        } catch (err: any) {
            console.error(err);
            toast.error(err.message || 'Fehler beim Abrufen der KI-Vorschläge.');
        } finally {
            setIsSuggesting(false);
        }
    };

    const handleCreateAnthology = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!title.trim()) {
            toast.error('Bitte gib einen Buchtitel ein.');
            return;
        }
        if (selectedStoryIds.length === 0) {
            toast.error('Keine Geschichten ausgewählt.');
            return;
        }

        setIsCreating(true);
        try {
            const newProject = await createAnthologyBook({
                title: title.trim(),
                subtitle: subtitle.trim() || undefined,
                author: author.trim() || undefined,
                genre,
                style,
                language,
                story_ids: selectedStoryIds,
                auto_generate_blurb: autoGenerateBlurb,
                model: selectedModel
            });

            toast.success(`Sammelband "${newProject.title}" mit ${selectedStoryIds.length} Geschichten erfolgreich erstellt!`);
            onCreated(newProject);
            onClose();
        } catch (err: any) {
            console.error(err);
            toast.error(err.message || 'Fehler beim Erstellen des Sammelbands.');
        } finally {
            setIsCreating(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in overflow-y-auto">
            <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden my-auto">
                
                {/* Header */}
                <div className="px-6 py-5 border-b border-slate-800/80 flex items-center justify-between bg-slate-900/60 sticky top-0 z-20 backdrop-blur-md">
                    <div className="flex items-center gap-3.5">
                        <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-amber-500/20 via-primary/20 to-indigo-500/20 border border-primary/30 flex items-center justify-center text-primary shadow-inner">
                            <Layers className="w-5 h-5" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white flex items-center gap-2">
                                Kurzgeschichten-Sammelband erstellen
                                <span className="text-xs px-2.5 py-0.5 rounded-full bg-primary/20 text-primary border border-primary/30 font-medium">
                                    Anthologie-Modus
                                </span>
                            </h2>
                            <p className="text-xs text-slate-400">
                                {step === 1 ? 'Schritt 1 von 2: Geschichten auswählen & Reihenfolge festlegen' : 'Schritt 2 von 2: Buch-Metadaten & KI-Titel generieren'}
                            </p>
                        </div>
                    </div>

                    <button 
                        onClick={onClose}
                        className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto p-6">
                    {step === 1 ? (
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                            
                            {/* Left Column: Story Picker & Filter */}
                            <div className="lg:col-span-7 flex flex-col gap-4">
                                
                                {/* Search & Genre Filter Bar */}
                                <div className="flex flex-col gap-2.5">
                                    <div className="relative">
                                        <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                                        <input 
                                            type="text" 
                                            placeholder="Geschichten nach Titel oder Genre durchsuchen..."
                                            value={searchQuery}
                                            onChange={e => setSearchQuery(e.target.value)}
                                            className="w-full pl-10 pr-4 py-2.5 bg-slate-950/60 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-primary transition-colors"
                                        />
                                        {searchQuery && (
                                            <button 
                                                onClick={() => setSearchQuery('')}
                                                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
                                            >
                                                <X className="w-4 h-4" />
                                            </button>
                                        )}
                                    </div>

                                    {/* Genre Filter Pills */}
                                    <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1 text-xs">
                                        <button
                                            type="button"
                                            onClick={() => setSelectedGenreFilter('all')}
                                            className={`px-3 py-1.5 rounded-lg border font-medium whitespace-nowrap transition-all ${
                                                selectedGenreFilter === 'all'
                                                    ? 'bg-primary/20 border-primary/40 text-white shadow-sm'
                                                    : 'bg-slate-950/40 border-slate-800/80 text-slate-400 hover:text-white hover:bg-slate-800'
                                            }`}
                                        >
                                            Alle ({stories.length})
                                        </button>
                                        {availableGenres.map(g => (
                                            <button
                                                key={g}
                                                type="button"
                                                onClick={() => setSelectedGenreFilter(g)}
                                                className={`px-3 py-1.5 rounded-lg border font-medium whitespace-nowrap transition-all ${
                                                    selectedGenreFilter === g
                                                        ? 'bg-primary/20 border-primary/40 text-white shadow-sm'
                                                        : 'bg-slate-950/40 border-slate-800/80 text-slate-400 hover:text-white hover:bg-slate-800'
                                                }`}
                                            >
                                                {g} ({stories.filter(s => s.genre === g).length})
                                            </button>
                                        ))}
                                    </div>

                                    {/* Quick Selection Actions */}
                                    <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
                                        <span>{availableStories.length} Geschichten gefunden</span>
                                        <div className="flex items-center gap-3">
                                            <button 
                                                type="button"
                                                onClick={handleSelectAllFiltered}
                                                className="text-primary hover:underline font-medium"
                                            >
                                                Alle gefilterten auswählen
                                            </button>
                                            {selectedStoryIds.length > 0 && (
                                                <button 
                                                    type="button"
                                                    onClick={handleDeselectAll}
                                                    className="text-slate-400 hover:text-red-400 transition-colors"
                                                >
                                                    Auswahl leeren
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Stories Scrollable List */}
                                <div className="space-y-2.5 max-h-[50vh] overflow-y-auto pr-1">
                                    {availableStories.length === 0 ? (
                                        <div className="py-12 text-center text-slate-500 bg-slate-950/30 rounded-2xl border border-slate-800/50">
                                            <BookOpen className="w-8 h-8 mx-auto mb-2 opacity-40" />
                                            <p className="text-sm font-medium">Keine Geschichten gefunden.</p>
                                            <p className="text-xs mt-1 text-slate-600">Passe deine Such- oder Genre-Filter an.</p>
                                        </div>
                                    ) : (
                                        availableStories.map(story => {
                                            const isSelected = selectedStoryIds.includes(story.id);
                                            const thumbUrl = getThumbUrl(story.id);
                                            
                                            return (
                                                <div 
                                                    key={story.id}
                                                    onClick={() => handleToggleStory(story.id)}
                                                    className={`p-3 rounded-2xl border transition-all cursor-pointer flex items-center gap-3.5 group ${
                                                        isSelected 
                                                            ? 'bg-primary/10 border-primary/50 shadow-md shadow-primary/5' 
                                                            : 'bg-slate-950/40 border-slate-800/60 hover:bg-slate-800/40 hover:border-slate-700'
                                                    }`}
                                                >
                                                    {/* Checkbox */}
                                                    <div className={`w-5 h-5 rounded-md flex items-center justify-center border transition-all shrink-0 ${
                                                        isSelected 
                                                            ? 'bg-primary border-primary text-white' 
                                                            : 'border-slate-700 bg-slate-900 group-hover:border-slate-500'
                                                    }`}>
                                                        {isSelected && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                                                    </div>

                                                    {/* Story Thumbnail */}
                                                    <div className="w-12 h-16 rounded-xl bg-slate-900 border border-slate-800 overflow-hidden shrink-0 relative flex items-center justify-center text-slate-600">
                                                        {story.image_url ? (
                                                            <img 
                                                                src={thumbUrl} 
                                                                alt={story.title} 
                                                                className="w-full h-full object-cover"
                                                                onError={(e) => {
                                                                    (e.target as HTMLElement).style.display = 'none';
                                                                }}
                                                            />
                                                        ) : (
                                                            <BookOpen className="w-5 h-5 opacity-40" />
                                                        )}
                                                    </div>

                                                    {/* Story Meta */}
                                                    <div className="flex-1 min-w-0">
                                                        <h4 className="text-sm font-semibold text-white truncate group-hover:text-primary transition-colors">
                                                            {story.title}
                                                        </h4>
                                                        <p className="text-xs text-slate-400 line-clamp-1 mt-0.5">
                                                            {story.description || story.prompt}
                                                        </p>
                                                        <div className="flex items-center gap-3 mt-1.5 text-[11px] text-slate-500">
                                                            <span className="px-2 py-0.5 rounded-md bg-slate-800/80 text-slate-300 border border-slate-700/50">
                                                                {story.genre || 'Story'}
                                                            </span>
                                                            <span className="flex items-center gap-1">
                                                                <Clock className="w-3 h-3 text-slate-400" />
                                                                {formatDuration(story.duration_seconds)}
                                                            </span>
                                                            <span className="flex items-center gap-1">
                                                                <FileText className="w-3 h-3 text-slate-400" />
                                                                ~{story.word_count || Math.round((story.duration_seconds || 300) / 60 * 150)} Wörter
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })
                                    )}
                                </div>
                            </div>

                            {/* Right Column: Selected Sequence & Book Band Overview */}
                            <div className="lg:col-span-5 flex flex-col gap-4 bg-slate-950/40 p-4 rounded-2xl border border-slate-800/80">
                                <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                                    <div>
                                        <h3 className="text-sm font-bold text-white flex items-center gap-2">
                                            <Layers className="w-4 h-4 text-primary" />
                                            Ausgewählte Reihenfolge
                                        </h3>
                                        <p className="text-xs text-slate-400">
                                            Wird als Kapitel 1 bis {stats.count} im Buchband angelegt
                                        </p>
                                    </div>
                                    <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-primary/20 text-primary border border-primary/30">
                                        {stats.count} Geschichten
                                    </span>
                                </div>

                                {/* Stats Bar */}
                                <div className="grid grid-cols-3 gap-2 bg-slate-900/80 p-3 rounded-xl border border-slate-800 text-center">
                                    <div>
                                        <div className="text-xs text-slate-400">Geschichten</div>
                                        <div className="text-base font-bold text-white mt-0.5">{stats.count}</div>
                                    </div>
                                    <div>
                                        <div className="text-xs text-slate-400">Wortanzahl</div>
                                        <div className="text-base font-bold text-primary mt-0.5">~{stats.estimatedWords.toLocaleString()}</div>
                                    </div>
                                    <div>
                                        <div className="text-xs text-slate-400">Buchseiten</div>
                                        <div className="text-base font-bold text-white mt-0.5">~{stats.estimatedPages} S.</div>
                                    </div>
                                </div>

                                {/* Ordered Stories Drag/Sort List */}
                                <div className="flex-1 overflow-y-auto space-y-2 max-h-[38vh] pr-1">
                                    {orderedSelectedStories.length === 0 ? (
                                        <div className="py-16 text-center text-slate-500">
                                            <Layers className="w-8 h-8 mx-auto mb-2 opacity-30" />
                                            <p className="text-sm font-medium">Noch keine Geschichten gewählt.</p>
                                            <p className="text-xs mt-1 text-slate-600">Wähle links die gewünschten Kurzgeschichten aus.</p>
                                        </div>
                                    ) : (
                                        orderedSelectedStories.map((story, idx) => (
                                            <div 
                                                key={story.id}
                                                className="p-2.5 bg-slate-900 border border-slate-800 rounded-xl flex items-center justify-between gap-3 group"
                                            >
                                                <div className="flex items-center gap-2.5 min-w-0">
                                                    <span className="w-6 h-6 rounded-lg bg-slate-800 border border-slate-700 text-[11px] font-bold text-slate-300 flex items-center justify-center shrink-0">
                                                        {idx + 1}
                                                    </span>
                                                    <div className="min-w-0">
                                                        <div className="text-xs font-semibold text-white truncate">
                                                            {story.title}
                                                        </div>
                                                        <div className="text-[10px] text-slate-400">
                                                            {story.genre} • {formatDuration(story.duration_seconds)}
                                                        </div>
                                                    </div>
                                                </div>

                                                <div className="flex items-center gap-1 shrink-0">
                                                    <button
                                                        type="button"
                                                        onClick={() => handleMoveOrder(idx, 'up')}
                                                        disabled={idx === 0}
                                                        className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:pointer-events-none"
                                                        title="Nach oben"
                                                    >
                                                        <ChevronUp className="w-3.5 h-3.5" />
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => handleMoveOrder(idx, 'down')}
                                                        disabled={idx === orderedSelectedStories.length - 1}
                                                        className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:pointer-events-none"
                                                        title="Nach unten"
                                                    >
                                                        <ChevronDown className="w-3.5 h-3.5" />
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => handleRemoveSelected(story.id)}
                                                        className="p-1 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                                                        title="Entfernen"
                                                    >
                                                        <Trash2 className="w-3.5 h-3.5" />
                                                    </button>
                                                </div>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>
                    ) : (
                        /* Step 2: Book Details & AI Synthesis */
                        <form onSubmit={handleCreateAnthology} className="space-y-6 max-w-3xl mx-auto">
                            
                            {/* AI Suggestion Banner */}
                            <div className="p-4 bg-gradient-to-r from-primary/10 via-indigo-500/10 to-amber-500/10 border border-primary/30 rounded-2xl flex items-center justify-between gap-4">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-xl bg-primary/20 text-primary flex items-center justify-center shrink-0 border border-primary/30">
                                        <Wand2 className="w-5 h-5 animate-pulse" />
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-bold text-white">KI-Veredelung & Titel-Generator</h4>
                                        <p className="text-xs text-slate-300">
                                            Analysiert deine {selectedStoryIds.length} Geschichten und schlägt passende Bestseller-Titel, Klappentexte & Cover-Prompts vor.
                                        </p>
                                    </div>
                                </div>

                                <button
                                    type="button"
                                    onClick={handleSuggestAiMetadata}
                                    disabled={isSuggesting}
                                    className="px-4 py-2 bg-primary hover:bg-primary-hover text-white text-xs font-bold rounded-xl flex items-center gap-2 transition-all shadow-lg shadow-primary/20 disabled:opacity-50 shrink-0"
                                >
                                    {isSuggesting ? (
                                        <>
                                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                            Analysiere Geschichten...
                                        </>
                                    ) : (
                                        <>
                                            <Sparkles className="w-3.5 h-3.5" />
                                            Titel & Klappentext vorschlagen
                                        </>
                                    )}
                                </button>
                            </div>

                            {/* Book Metadata Form */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                
                                {/* Title */}
                                <div className="md:col-span-2">
                                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                                        Buchtitel des Sammelbands *
                                    </label>
                                    <input 
                                        type="text" 
                                        required
                                        placeholder="z. B. 10 Sinnliche Nächte: Erotische Kurzgeschichten"
                                        value={title}
                                        onChange={e => setTitle(e.target.value)}
                                        className="w-full px-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-primary transition-colors"
                                    />
                                </div>

                                {/* Subtitle */}
                                <div className="md:col-span-2">
                                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                                        Untertitel (optional)
                                    </label>
                                    <input 
                                        type="text" 
                                        placeholder="z. B. Ein exklusiver Sammelband verführerischer Liebesgeschichten"
                                        value={subtitle}
                                        onChange={e => setSubtitle(e.target.value)}
                                        className="w-full px-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-primary transition-colors"
                                    />
                                </div>

                                {/* Author / Pen Name */}
                                <div>
                                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                                        Autorenname / Pseudonym
                                    </label>
                                    <input 
                                        type="text" 
                                        placeholder="z. B. Dirk Proessel oder Künstlername"
                                        value={author}
                                        onChange={e => setAuthor(e.target.value)}
                                        className="w-full px-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-primary transition-colors"
                                    />
                                </div>

                                {/* Genre */}
                                <div>
                                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                                        Hauptgenre
                                    </label>
                                    <select
                                        value={genre}
                                        onChange={e => setGenre(e.target.value)}
                                        className="w-full px-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-primary transition-colors"
                                    >
                                        {GENRES.map(g => (
                                            <option key={g.value} value={g.value}>{g.label}</option>
                                        ))}
                                    </select>
                                </div>

                                {/* Author Style */}
                                <div>
                                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                                        Autorenstil / Inspiration
                                    </label>
                                    <select
                                        value={style}
                                        onChange={e => setStyle(e.target.value)}
                                        className="w-full px-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-primary transition-colors"
                                    >
                                        {AUTHORS.map(a => (
                                            <option key={a.id} value={a.id}>{formatAuthorStyles(a.id)}</option>
                                        ))}
                                    </select>
                                </div>

                                {/* Language */}
                                <div>
                                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                                        Buch-Sprache
                                    </label>
                                    <div className="grid grid-cols-2 gap-2">
                                        <button
                                            type="button"
                                            onClick={() => setLanguage('de')}
                                            className={`py-2.5 px-3 rounded-xl border text-xs font-bold transition-all ${
                                                language === 'de'
                                                    ? 'bg-primary/20 border-primary text-white shadow-sm'
                                                    : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-white'
                                            }`}
                                        >
                                            🇩🇪 Deutsch
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setLanguage('en')}
                                            className={`py-2.5 px-3 rounded-xl border text-xs font-bold transition-all ${
                                                language === 'en'
                                                    ? 'bg-primary/20 border-primary text-white shadow-sm'
                                                    : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-white'
                                            }`}
                                        >
                                            🇬🇧 Englisch
                                        </button>
                                    </div>
                                </div>

                                {/* AI Model Selection */}
                                <div className="md:col-span-2">
                                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                                        KI-Modell für Synthese & Lektorat
                                    </label>
                                    <select
                                        value={selectedModel}
                                        onChange={e => setSelectedModel(e.target.value)}
                                        className="w-full px-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-primary transition-colors"
                                    >
                                        {TEXT_MODELS.map(m => (
                                            <option key={m.value} value={m.value}>{m.label}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            {/* AI Suggestions Preview Accordion if present */}
                            {aiSuggestion && (
                                <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-2xl space-y-3 animate-fade-in text-xs">
                                    <div className="font-bold text-white flex items-center gap-2">
                                        <Sparkles className="w-3.5 h-3.5 text-primary" />
                                        Generierte Buch-Elemente (Vorschau):
                                    </div>
                                    {aiSuggestion.blurb && (
                                        <div>
                                            <span className="font-semibold text-slate-400">Klappentext: </span>
                                            <p className="text-slate-300 mt-1 italic whitespace-pre-line bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/80">
                                                {aiSuggestion.blurb}
                                            </p>
                                        </div>
                                    )}
                                    {aiSuggestion.cover_prompt && (
                                        <div>
                                            <span className="font-semibold text-slate-400">Vorgeschlagener Cover-Prompt: </span>
                                            <p className="text-slate-300 mt-1 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/80 text-[11px] font-mono">
                                                {aiSuggestion.cover_prompt}
                                            </p>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Auto-generate blurb checkbox */}
                            <label className="flex items-center gap-2.5 cursor-pointer text-xs text-slate-300">
                                <input 
                                    type="checkbox"
                                    checked={autoGenerateBlurb}
                                    onChange={e => setAutoGenerateBlurb(e.target.checked)}
                                    className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-primary focus:ring-primary"
                                />
                                <span>Vorwort, Klappentext & Cover-Prompt beim Erstellen automatisch verfeinern</span>
                            </label>
                        </form>
                    )}
                </div>

                {/* Footer Controls */}
                <div className="px-6 py-4 border-t border-slate-800/80 bg-slate-900/80 flex items-center justify-between sticky bottom-0 z-20 backdrop-blur-md">
                    {step === 1 ? (
                        <>
                            <div className="text-xs text-slate-400">
                                <span className="font-bold text-white">{selectedStoryIds.length}</span> Geschichten gewählt ({stats.estimatedWords.toLocaleString()} Wörter)
                            </div>
                            <button
                                type="button"
                                onClick={handleGoToStep2}
                                disabled={selectedStoryIds.length === 0}
                                className="px-6 py-2.5 bg-primary hover:bg-primary-hover disabled:opacity-40 disabled:pointer-events-none text-white text-xs font-bold rounded-xl flex items-center gap-2 transition-all shadow-lg shadow-primary/20"
                            >
                                Weiter zu Buchdetails
                                <ArrowRight className="w-4 h-4" />
                            </button>
                        </>
                    ) : (
                        <>
                            <button
                                type="button"
                                onClick={() => setStep(1)}
                                disabled={isCreating}
                                className="px-4 py-2.5 text-slate-400 hover:text-white text-xs font-semibold rounded-xl flex items-center gap-2 transition-colors"
                            >
                                <ArrowLeft className="w-4 h-4" />
                                Zurück zur Auswahl
                            </button>

                            <button
                                type="button"
                                onClick={handleCreateAnthology}
                                disabled={isCreating || !title.trim()}
                                className="px-6 py-2.5 bg-gradient-to-r from-primary to-indigo-600 hover:from-primary-hover hover:to-indigo-500 disabled:opacity-50 text-white text-xs font-bold rounded-xl flex items-center gap-2 transition-all shadow-lg shadow-primary/20"
                            >
                                {isCreating ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Erstelle Buchband & importiere Texte...
                                    </>
                                ) : (
                                    <>
                                        <BookOpen className="w-4 h-4" />
                                        Sammelband erstellen & im Editor öffnen
                                    </>
                                )}
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

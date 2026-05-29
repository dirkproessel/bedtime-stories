import { useEffect, useState } from 'react';
import { useStore } from '../store/useStore';
import { Mic, Globe, Lock, Play, Loader2, User, Plus, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { getVoicePreviewUrl } from '../lib/api';

export default function AdminVoiceManagement() {
    const { 
        adminClonedVoices, 
        adminSystemVoices, 
        loadAdminVoices, 
        toggleAdminVoice, 
        addAdminVoice,
        isLoading 
    } = useStore();

    const [showModal, setShowModal] = useState(false);
    const [name, setName] = useState('');
    const [engine, setEngine] = useState('fish');
    const [gender, setGender] = useState('neutral');
    const [description, setDescription] = useState('');
    const [fishVoiceId, setFishVoiceId] = useState('');
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        loadAdminVoices();
    }, [loadAdminVoices]);

    const handleToggle = async (type: 'system' | 'clone', id: string) => {
        try {
            await toggleAdminVoice(type, id);
            toast.success('Stimmenstatus aktualisiert');
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Aktualisieren');
        }
    };

    const playPreview = (key: string) => {
        const audio = new Audio(getVoicePreviewUrl(key));
        audio.play().catch(e => {
            console.error("Preview failed:", e);
            toast.error("Vorschau konnte nicht abgespielt werden");
        });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!name.trim() || !fishVoiceId.trim()) {
            toast.error('Bitte alle Pflichtfelder ausfüllen');
            return;
        }

        setSubmitting(true);
        try {
            await addAdminVoice({
                name: name.trim(),
                engine,
                gender,
                description: description.trim() || undefined,
                fish_voice_id: fishVoiceId.trim()
            });
            toast.success('System-Stimme erfolgreich hinzugefügt');
            setShowModal(false);
            // Reset form
            setName('');
            setEngine('fish');
            setGender('neutral');
            setDescription('');
            setFishVoiceId('');
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Erstellen der Stimme');
        } finally {
            setSubmitting(false);
        }
    };

    if (isLoading && adminSystemVoices.length === 0) {
        return (
            <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-8 pb-12">
            
            {/* System Voices Section */}
            <section className="space-y-4">
                <div className="flex items-center justify-between px-2">
                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                        <Globe className="w-5 h-5 text-blue-400" />
                        System-Stimmen (Standard)
                    </h2>
                    <div className="flex items-center gap-4">
                        <span className="text-xs text-slate-500 uppercase tracking-widest font-bold hidden sm:inline">
                            {adminSystemVoices.length} Verfügbar
                        </span>
                        <button 
                            onClick={() => setShowModal(true)}
                            className="flex items-center gap-1.5 bg-emerald-500 hover:bg-emerald-600 text-slate-950 text-xs font-bold px-3.5 py-2 rounded-xl transition-all shadow-lg shadow-emerald-500/10 hover:shadow-emerald-500/20"
                        >
                            <Plus className="w-4 h-4" />
                            Stimme hinzufügen
                        </button>
                    </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {adminSystemVoices.map((voice) => (
                        <div key={voice.id} className="glass-panel rounded-2xl p-4 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${voice.is_active ? 'bg-blue-500/20 text-blue-400' : 'bg-white/5 text-slate-500'}`}>
                                    <Mic className="w-5 h-5" />
                                </div>
                                <div>
                                    <div className="text-white font-medium flex items-center gap-2">
                                        {voice.name}
                                        <span className="text-[10px] bg-white/10 text-slate-400 px-1.5 py-0.5 rounded font-mono uppercase">
                                            {voice.engine}
                                        </span>
                                    </div>
                                    <div className="text-xs text-slate-500 font-mono truncate max-w-[180px]">
                                        ID: {voice.id}
                                    </div>
                                    {voice.description && (
                                        <div className="text-[10px] text-blue-400/70 italic mt-0.5 max-w-[200px] truncate">
                                            {voice.description}
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="flex items-center gap-2">
                                <button 
                                    onClick={() => playPreview(voice.id)}
                                    className="p-2 text-slate-400 hover:text-white hover:bg-white/5 rounded-lg transition-all"
                                    title="Vorschau abspielen"
                                >
                                    <Play className="w-4 h-4" />
                                </button>
                                <button
                                    onClick={() => handleToggle('system', voice.id)}
                                    className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                                        voice.is_active 
                                        ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' 
                                        : 'bg-white/5 text-slate-500 border border-white/10'
                                    }`}
                                >
                                    {voice.is_active ? 'AKTIV' : 'INAKTIV'}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            {/* Cloned Voices Section */}
            <section className="space-y-4">
                <div className="flex items-center justify-between px-2">
                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                        <User className="w-5 h-5 text-emerald-400" />
                        Nutzer-Stimmen (Klone)
                    </h2>
                    <span className="text-xs text-slate-500 uppercase tracking-widest font-bold">
                        {adminClonedVoices.length} Klone
                    </span>
                </div>

                <div className="space-y-3">
                    {adminClonedVoices.map((voice) => (
                        <div key={voice.id} className="glass-panel rounded-2xl p-4 flex items-center justify-between group">
                            <div className="flex items-center gap-4">
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center bg-emerald-500/10 text-emerald-500`}>
                                    <User className="w-5 h-5" />
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-white font-medium flex items-center gap-2">
                                        {voice.name}
                                        <span className="text-[10px] text-slate-500 font-normal">
                                            von {voice.user_name}
                                        </span>
                                    </span>
                                    <div className="flex flex-col gap-0.5 mt-0.5">
                                        <div className="text-[10px] text-slate-500 font-mono flex items-center gap-1">
                                            <span className="text-slate-600">INT:</span> {voice.id}
                                        </div>
                                        <div className="text-[10px] text-amber-500/70 font-mono flex items-center gap-1">
                                            <span className="text-slate-600">FISH:</span> {voice.fish_voice_id}
                                        </div>
                                        {voice.description && (
                                            <div className="text-[10px] text-emerald-400/80 italic mt-0.5 max-w-[250px] truncate">
                                                ★ {voice.description}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center gap-3">
                                <button 
                                    onClick={() => playPreview(voice.id)}
                                    className="p-2 text-slate-400 hover:text-white hover:bg-white/5 rounded-lg transition-all"
                                >
                                    <Play className="w-4 h-4" />
                                </button>
                                
                                <button
                                    onClick={() => handleToggle('clone', voice.id)}
                                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                                        voice.is_public 
                                        ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' 
                                        : 'bg-white/5 text-slate-500 border border-white/10'
                                    }`}
                                >
                                    {voice.is_public ? <Globe className="w-3.5 h-3.5" /> : <Lock className="w-3.5 h-3.5" />}
                                    {voice.is_public ? 'ÖFFENTLICH' : 'PRIVAT'}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>

                {adminClonedVoices.length === 0 && (
                    <div className="text-center py-12 text-slate-500 italic border border-dashed border-white/5 rounded-2xl">
                        Keine Klone vorhanden.
                    </div>
                )}
            </section>

            {/* Premium Glass Modal Form */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md transition-all">
                    <div className="glass-panel w-full max-w-md rounded-3xl overflow-hidden shadow-2xl border border-white/10 animate-in fade-in zoom-in-95 duration-200">
                        <div className="px-6 py-5 border-b border-white/5 flex items-center justify-between">
                            <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                <Plus className="w-5 h-5 text-emerald-400" />
                                Neue System-Stimme
                            </h3>
                            <button 
                                onClick={() => setShowModal(false)}
                                className="p-1.5 text-slate-400 hover:text-white hover:bg-white/5 rounded-xl transition-all"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <form onSubmit={handleSubmit} className="p-6 space-y-4">
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Anzeigename</label>
                                <input 
                                    type="text" 
                                    required
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="z.B. Christoph (deutsch)"
                                    className="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 transition-all text-sm"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Anbieter</label>
                                    <select 
                                        value={engine}
                                        onChange={(e) => setEngine(e.target.value)}
                                        className="w-full bg-slate-900 border border-white/10 rounded-2xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 transition-all text-sm"
                                    >
                                        <option value="fish">Fish Audio</option>
                                        <option value="xai">xAI</option>
                                    </select>
                                </div>

                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Geschlecht</label>
                                    <select 
                                        value={gender}
                                        onChange={(e) => setGender(e.target.value)}
                                        className="w-full bg-slate-900 border border-white/10 rounded-2xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 transition-all text-sm"
                                    >
                                        <option value="male">Männlich</option>
                                        <option value="female">Weiblich</option>
                                        <option value="neutral">Neutral</option>
                                    </select>
                                </div>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                    {engine === 'fish' ? 'Fish Voice ID' : 'xAI Voice ID'}
                                </label>
                                <input 
                                    type="text" 
                                    required
                                    value={fishVoiceId}
                                    onChange={(e) => setFishVoiceId(e.target.value)}
                                    placeholder={engine === 'fish' ? 'z.B. bbe1ddaa9dfc4f5187e8ba527c1595c6' : 'z.B. 458705c07139'}
                                    className="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 transition-all font-mono text-xs"
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Beschreibung (optional)</label>
                                <textarea 
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    placeholder="z.B. Ausgewogene, warme deutsche Stimme."
                                    rows={2}
                                    className="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 transition-all resize-none text-sm"
                                />
                            </div>

                            <div className="pt-4 flex gap-3">
                                <button 
                                    type="button"
                                    onClick={() => setShowModal(false)}
                                    className="flex-1 bg-white/5 hover:bg-white/10 text-white font-bold py-3.5 rounded-2xl border border-white/10 transition-all text-sm"
                                >
                                    Abbrechen
                                </button>
                                <button 
                                    type="submit"
                                    disabled={submitting}
                                    className="flex-1 bg-emerald-500 hover:bg-emerald-600 disabled:bg-emerald-500/50 text-slate-950 font-bold py-3.5 rounded-2xl transition-all flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/25 text-sm"
                                >
                                    {submitting ? (
                                        <>
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                            Wird gespeichert...
                                        </>
                                    ) : (
                                        'Hinzufügen'
                                    )}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

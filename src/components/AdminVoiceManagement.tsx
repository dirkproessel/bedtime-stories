import { useEffect } from 'react';
import { useStore } from '../store/useStore';
import { Mic, Globe, Lock, Play, Loader2, User } from 'lucide-react';
import toast from 'react-hot-toast';
import { getVoicePreviewUrl } from '../lib/api';

export default function AdminVoiceManagement() {
    const { 
        adminClonedVoices, 
        adminSystemVoices, 
        loadAdminVoices, 
        toggleAdminVoice, 
        isLoading 
    } = useStore();

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
                    <span className="text-xs text-slate-500 uppercase tracking-widest font-bold">
                        {adminSystemVoices.length} Verfügbar
                    </span>
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
                                    <div className="text-xs text-slate-500 font-mono truncate max-w-[150px]">
                                        ID: {voice.id}
                                    </div>
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
        </div>
    );
}

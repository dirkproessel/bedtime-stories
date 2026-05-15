import { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { updateKindleEmail, updateUsername, uploadProfilePicture, unlinkAlexa, cloneVoice, updateCustomVoice, deleteCustomVoice, adminFetchSettings, adminUpdateSetting, adminListVoices, linkWhatsAppPhone } from '../lib/api';
import { LogOut, Download, Mail, Check, Loader2, Radio, Copy, User, Shield, Camera, Mic, Music, Trash2, Globe, Lock, Venus, Mars, Users, Settings2, Sparkles, Image as ImageIcon, MessageCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import ProfilePictureUpload from './ProfilePictureUpload';

function VoiceCloneItem({ voice, onUpdate }: { voice: any, onUpdate: (user: any) => void }) {
    const [name, setName] = useState(voice.name);
    const [isSaving, setIsSaving] = useState(false);
    
    const handleSave = async () => {
        setIsSaving(true);
        try {
            const updatedUser = await updateCustomVoice(voice.id, { name });
            onUpdate(updatedUser);
            toast.success('Name gespeichert');
        } catch(e: any) {
            toast.error(e.message);
        } finally {
            setIsSaving(false);
        }
    };

    const handleTogglePublic = async () => {
        setIsSaving(true);
        try {
            const updatedUser = await updateCustomVoice(voice.id, { is_public: !voice.is_public });
            onUpdate(updatedUser);
            toast.success(!voice.is_public ? 'Stimme ist nun öffentlich' : 'Stimme ist nun privat');
        } catch(e: any) {
            toast.error(e.message);
        } finally {
            setIsSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!confirm('Stimme wirklich löschen?')) return;
        try {
            const updatedUser = await deleteCustomVoice(voice.id);
            onUpdate(updatedUser);
            toast.success('Stimme gelöscht');
        } catch(e: any) {
            toast.error(e.message);
        }
    };

    return (
        <div className="p-3 bg-white/5 border border-white/10 rounded-xl space-y-2 relative group">
            <div className="flex items-center justify-between">
               <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">ID: {voice.id.substring(0,8)}</span>
               <div className="flex items-center gap-2">
                   <button onClick={handleTogglePublic} title={voice.is_public ? "Öffentlich (für alle sichtbar)" : "Privat (nur für dich)"} className="p-1 hover:bg-white/10 rounded transition-colors duration-200">
                       {voice.is_public ? <Globe className="w-4 h-4 text-emerald-400" /> : <Lock className="w-4 h-4 text-slate-400" />}
                   </button>
                   <button onClick={handleDelete} className="p-1 hover:bg-red-500/20 text-red-400 rounded transition-colors duration-200" title="Stimme löschen">
                       <Trash2 className="w-4 h-4" />
                   </button>
               </div>
            </div>
            <div className="flex flex-col gap-1 relative">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="flex-1 px-3 py-1.5 bg-black/20 border border-white/5 rounded-lg focus:ring-1 focus:ring-emerald-500/50 outline-none text-sm text-white"
                    />
                    {(name !== voice.name) && (
                        <button
                            onClick={handleSave}
                            disabled={isSaving}
                            className="px-3 py-1.5 bg-emerald-500 hover:bg-emerald-400 text-white rounded-lg flex items-center justify-center disabled:opacity-50 transition-colors"
                        >
                            {isSaving ? <Loader2 className="w-4 h-4 animate-spin"/> : <Check className="w-4 h-4"/>}
                        </button>
                    )}
                </div>
                {(voice.gender || voice.description) && (
                    <div className="text-[10px] text-slate-500 italic px-1 flex gap-1.5 items-center">
                        {voice.gender === 'female' ? <Venus className="w-3.5 h-3.5 text-pink-500/50" /> :
                         voice.gender === 'male' ? <Mars className="w-3.5 h-3.5 text-blue-500/50" /> : 
                         voice.gender === 'neutral' ? <Users className="w-3.5 h-3.5 text-slate-500/50" /> : null}
                        {(voice.gender && voice.description) && <span className="text-slate-700">&bull;</span>}
                        {voice.description && <span>{voice.description}</span>}
                    </div>
                )}
            </div>
        </div>
    );
}

function SystemSettingsSection() {
    const [settings, setSettings] = useState<any[]>([]);
    const [allVoices, setAllVoices] = useState<{ clones: any[], system: any[] }>({ clones: [], system: [] });
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState<string | null>(null);

    const loadData = async () => {
        try {
            const [settingsData, voicesData] = await Promise.all([
                adminFetchSettings(),
                adminListVoices()
            ]);
            setSettings(settingsData);
            setAllVoices(voicesData);
        } catch (e: any) {
            toast.error('Fehler beim Laden der Systemdaten');
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleUpdate = async (key: string, value: string) => {
        setIsSaving(key);
        try {
            await adminUpdateSetting(key, value);
            toast.success('Einstellung gespeichert');
            setSettings(prev => prev.map(s => s.key === key ? { ...s, value } : s));
        } catch (e: any) {
            toast.error(e.message);
        } finally {
            setIsSaving(null);
        }
    };

    if (isLoading) return <div className="p-4 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto text-slate-500" /></div>;

    const textModel = settings.find(s => s.key === 'gemini_text_model')?.value || '';
    const imageModel = settings.find(s => s.key === 'gemini_image_model')?.value || '';
    const alexaVoice = settings.find(s => s.key === 'alexa_default_voice')?.value || 'seraphina';

    return (
        <div className="w-full glass-panel rounded-3xl p-6 space-y-4 border border-purple-500/20">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center flex-shrink-0">
                    <Settings2 className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                    <h3 className="font-bold text-white text-sm">System-Einstellungen</h3>
                    <p className="text-xs text-slate-400">KI-Modelle global konfigurieren</p>
                </div>
            </div>

            <div className="space-y-4 pt-2">
                {/* Text Model */}
                <div className="space-y-2">
                    <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">
                        <Sparkles className="w-3 h-3" />
                        Text Generierung
                    </div>
                    <select 
                        value={textModel}
                        onChange={(e) => handleUpdate('gemini_text_model', e.target.value)}
                        disabled={isSaving === 'gemini_text_model'}
                        className="w-full px-4 py-2.5 bg-slate-900 border border-white/10 rounded-xl focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500/50 outline-none transition-all text-white text-sm"
                    >
                        <option value="gemini-3.1-flash-lite">Gemini 3.1 Flash (Effizient & Schnell)</option>
                        <option value="gemini-3.1-pro-preview">Gemini 3.1 Pro (Meisterhafte Lyrik)</option>
                        <option value="deepseek-v4-flash">DeepSeek V4 Flash (Neu & Schnell)</option>
                        <option value="deepseek-v4-pro">DeepSeek V4 Pro (High-End Reasoning)</option>
                    </select>
                </div>

                {/* Image Model */}
                <div className="space-y-2">
                    <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">
                        <ImageIcon className="w-3 h-3" />
                        Cover Bilder
                    </div>
                    <select 
                        value={imageModel}
                        onChange={(e) => handleUpdate('gemini_image_model', e.target.value)}
                        disabled={isSaving === 'gemini_image_model'}
                        className="w-full px-4 py-2.5 bg-slate-900 border border-white/10 rounded-xl focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500/50 outline-none transition-all text-white text-sm"
                    >
                        <option value="gemini-3.1-flash-image-preview">Gemini 3.1 Flash (512px - Günstig)</option>
                        <option value="gemini-3-pro-image-preview">Gemini 3.0 Pro (Premium Qualität)</option>
                        <option value="fal-ai/flux/schnell">Flux/schnell (fal.ai)</option>
                    </select>
                </div>

                {/* Alexa Voice */}
                <div className="space-y-2">
                    <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">
                        <Mic className="w-3 h-3" />
                        Alexa Vorlese-Stimme
                    </div>
                    <select 
                        value={alexaVoice}
                        onChange={(e) => handleUpdate('alexa_default_voice', e.target.value)}
                        disabled={isSaving === 'alexa_default_voice'}
                        className="w-full px-4 py-2.5 bg-slate-900 border border-white/10 rounded-xl focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500/50 outline-none transition-all text-white text-sm"
                    >
                        <optgroup label="System-Stimmen">
                            {allVoices.system.map(v => (
                                <option key={v.id} value={v.id} className="bg-slate-900 text-white">
                                    {v.name} ({v.engine}{!v.is_active ? ' - Inaktiv' : ''})
                                </option>
                            ))}
                        </optgroup>
                        {allVoices.clones.length > 0 && (
                            <optgroup label="Nutzer-Klone">
                                {allVoices.clones.map(v => (
                                    <option key={v.id} value={v.id} className="bg-slate-900 text-white">
                                        {v.name} (Klon von {v.user_name || 'Unbekannt'}){!v.is_public ? ' - Privat' : ''}
                                    </option>
                                ))}
                            </optgroup>
                        )}
                    </select>
                </div>
            </div>
        </div>
    );
}

export default function AccountScreen() {
    const { user, logout, playlist, removeFromPlaylist, clearPlaylist, upgradeGuest } = useStore();
    const isGuest = user?.email?.endsWith('@storyja.guest') ?? false;
    const [kindleEmail, setKindleEmail] = useState(user?.kindle_email || '');
    const [username, setUsername] = useState(isGuest ? '' : user?.username || user?.email || '');
    const [upgradeEmail, setUpgradeEmail] = useState('');
    const [upgradePassword, setUpgradePassword] = useState('');
    const [guestAuthMode, setGuestAuthMode] = useState<'register' | 'login'>('register');
    const [isSavingKindle, setIsSavingKindle] = useState(false);
    const [isSavingUsername, setIsSavingUsername] = useState(false);
    const [showAvatarUpload, setShowAvatarUpload] = useState(false);
    const [isCloning, setIsCloning] = useState(false);
    const [whatsappPhone, setWhatsappPhone] = useState(user?.whatsapp_phone || '');
    const [isSavingWhatsapp, setIsSavingWhatsapp] = useState(false);

    const handleSaveKindle = async () => {
        if (kindleEmail === user?.kindle_email) return;
        setIsSavingKindle(true);
        try {
            await updateKindleEmail(kindleEmail);
            toast.success('Kindle-Adresse gespeichert!');
            useStore.setState({ user: { ...user!, kindle_email: kindleEmail } });
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Speichern');
        } finally {
            setIsSavingKindle(false);
        }
    };

    const handleSaveUsername = async () => {
        if (username === user?.username) return;
        setIsSavingUsername(true);
        try {
            await updateUsername(username);
            toast.success('Benutzername aktualisiert!');
            useStore.setState({ user: { ...user!, username } });
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Speichern');
        } finally {
            setIsSavingUsername(false);
        }
    };

    const rssUrl = `${window.location.protocol}//${window.location.host.replace(':5173', ':8000')}/api/feed.xml`;
    const copyToClipboard = () => {
        navigator.clipboard.writeText(rssUrl);
        toast.success('RSS-Link kopiert!');
    };

    const handleAvatarUpload = async (blob: Blob) => {
        try {
            const updatedUser = await uploadProfilePicture(blob);
            useStore.setState({ user: updatedUser });
            setShowAvatarUpload(false);
            toast.success('Profilbild aktualisiert!');
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Hochladen');
        }
    };

    const handleVoiceUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        // Check file size (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
            toast.error('Datei ist zu groß (max. 10MB)');
            return;
        }

        setIsCloning(true);
        const toastId = toast.loading('Stimme wird geklont... dies kann einen Moment dauern.');
        
        try {
            const updatedUser = await cloneVoice(file);
            useStore.setState({ user: updatedUser });
            await useStore.getState().loadVoices(); // Refresh global voice list
            toast.success('Stimme erfolgreich geklont!', { id: toastId });
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Klonen', { id: toastId });
        } finally {
            setIsCloning(false);
        }
    };

    const handleUnlinkAlexa = async () => {
        if (!window.confirm('Möchtest du die Verbindung zu Alexa wirklich trennen?')) return;
        try {
            await unlinkAlexa();
            useStore.setState({ user: { ...user!, alexa_user_id: undefined } });
            toast.success('Verknüpfung aufgehoben');
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Trennen');
        }
    };

    const handleSaveWhatsapp = async () => {
        if (whatsappPhone === user?.whatsapp_phone) return;
        setIsSavingWhatsapp(true);
        try {
            const result = await linkWhatsAppPhone(whatsappPhone);
            if (result.migrated) {
                toast.success(`Nummer verknüpft! ${result.count} Geschichten wurden migriert.`);
            } else {
                toast.success('WhatsApp-Nummer verknüpft!');
            }
            useStore.setState({ user: { ...user!, whatsapp_phone: whatsappPhone } });
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Verknüpfen');
        } finally {
            setIsSavingWhatsapp(false);
        }
    };

    if (!user) return null;

    return (
        <div className="flex flex-col items-center max-w-lg mx-auto p-6 md:p-12 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-32">
            
            {/* Profile Header */}
            <div className="w-full text-center space-y-2">
                <div className="relative inline-block group">
                    <div className="w-24 h-24 rounded-full bg-emerald-500/10 border-2 border-emerald-500/20 flex items-center justify-center mx-auto mb-4 overflow-hidden relative">
                        {user.avatar_url ? (
                            <img 
                                src={user.avatar_url + "?t=" + Date.now()} 
                                alt="Profil" 
                                className="w-full h-full object-cover" 
                            />
                        ) : (
                            <User className="w-12 h-12 text-emerald-500" />
                        )}
                        <button 
                            onClick={() => setShowAvatarUpload(true)}
                            className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                        >
                            <Camera className="w-8 h-8 text-white" />
                        </button>
                    </div>
                    {user.is_admin && (
                        <div className="absolute -top-1 -right-1 bg-emerald-500 text-white text-xs font-bold px-2 py-0.5 rounded-full flex items-center gap-1 shadow-lg border border-emerald-400 z-10">
                            <Shield className="w-3 h-3" />
                            ADMIN
                        </div>
                    )}
                </div>
                <h2 className="text-2xl font-bold text-white tracking-tight">
                    {user.username || 'Dein Profil'}
                </h2>
                <div className="flex items-center justify-center gap-2 text-slate-400 text-sm">
                    <Mail className="w-4 h-4" />
                    <span>{isGuest ? 'Gast-Account' : user.email}</span>
                </div>
            </div>

            {isGuest ? (
                <div className="w-full glass-panel rounded-3xl p-6 space-y-6 border-2 border-primary/30 relative overflow-hidden">
                    <div className="flex bg-slate-900/50 p-1 rounded-xl mb-2 border border-slate-800 relative z-10">
                        <button
                            onClick={() => setGuestAuthMode('register')}
                            className={`flex-1 py-2 text-sm font-bold rounded-lg transition-all ${guestAuthMode === 'register' ? 'bg-primary text-white shadow-md' : 'text-slate-400 hover:text-white'}`}
                        >
                            Neu registrieren
                        </button>
                        <button
                            onClick={() => setGuestAuthMode('login')}
                            className={`flex-1 py-2 text-sm font-bold rounded-lg transition-all ${guestAuthMode === 'login' ? 'bg-primary text-white shadow-md' : 'text-slate-400 hover:text-white'}`}
                        >
                            Anmelden
                        </button>
                    </div>

                    <div className="text-center space-y-2 mb-6">
                        <h3 className="text-xl font-bold text-white">
                            {guestAuthMode === 'register' ? 'Konto erstellen' : 'Mit bestehendem Konto verbinden'}
                        </h3>
                        <p className="text-sm text-slate-400">
                            {guestAuthMode === 'register' 
                                ? 'Speichere deine Geschichten dauerhaft und schalte alle Funktionen (Favoriten, Veröffentlichen, Kindle-Export) frei.'
                                : 'Melde dich an, um deine neuen Geschichten automatisch in deinen bestehenden Account zu übertragen.'}
                        </p>
                    </div>
                    <form 
                        onSubmit={async (e) => {
                            e.preventDefault();
                            try {
                                if (guestAuthMode === 'register') {
                                    await upgradeGuest(upgradeEmail, upgradePassword);
                                    toast.success("Konto erfolgreich erstellt!");
                                } else {
                                    await useStore.getState().loginAndMergeGuest(upgradeEmail, upgradePassword);
                                    toast.success("Accounts erfolgreich zusammengeführt!");
                                }
                            } catch (e: any) {
                                toast.error(e.message || "Fehler beim Vorgang");
                            }
                        }}
                        className="space-y-4 relative z-10"
                    >
                        <input
                            type="email"
                            value={upgradeEmail}
                            onChange={(e) => setUpgradeEmail(e.target.value)}
                            placeholder="E-Mail Adresse"
                            className="w-full px-4 py-3 bg-slate-900/80 border border-slate-700 rounded-xl focus:ring-2 focus:ring-primary/50 outline-none transition-all text-white"
                            required
                        />
                        <input
                            type="password"
                            value={upgradePassword}
                            onChange={(e) => setUpgradePassword(e.target.value)}
                            placeholder="Passwort"
                            className="w-full px-4 py-3 bg-slate-900/80 border border-slate-700 rounded-xl focus:ring-2 focus:ring-primary/50 outline-none transition-all text-white"
                            required
                        />
                        <button type="submit" className="btn-primary w-full py-3 shadow-lg shadow-primary/20">
                            {guestAuthMode === 'register' ? 'Jetzt Registrieren' : 'Jetzt Anmelden & Zusammenführen'}
                        </button>
                    </form>
                </div>
            ) : (
                <>
                    {/* Profile Settings */}
            <div className="w-full glass-panel rounded-3xl p-6 space-y-6">
                <div className="space-y-4">
                    <div className="space-y-2">
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                            Benutzername
                        </label>
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="Dein Anzeigename"
                                className="flex-1 px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500/50 outline-none transition-all text-white placeholder:text-slate-600"
                            />
                            <button
                                onClick={handleSaveUsername}
                                disabled={isSavingUsername || username === user?.username}
                                className="px-4 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-white font-medium rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-emerald-500/20"
                            >
                                {isSavingUsername ? <Loader2 className="w-5 h-5 animate-spin" /> : <Check className="w-5 h-5" />}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Voice Cloning Section */}
            <div className="w-full glass-panel rounded-3xl p-6 space-y-4 border border-emerald-500/20">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                        <Mic className="w-5 h-5 text-emerald-400" />
                    </div>
                    <div className="flex-1">
                        <h3 className="font-bold text-white text-sm">Stimmen-Klone (AI)</h3>
                        <p className="text-xs text-slate-400">
                            {user.custom_voices && user.custom_voices.length > 0 ? `${user.custom_voices.length} von 5 Stimmen aktiv` : 'Lerne die KI deine Stimme'}
                        </p>
                    </div>
                    {user.custom_voices && user.custom_voices.length > 0 && <Music className="w-4 h-4 text-emerald-400 animate-pulse" />}
                </div>

                <div className="space-y-3">
                    {user.custom_voices && user.custom_voices.length > 0 ? (
                        <div className="space-y-3">
                            {user.custom_voices.map(voice => (
                                <VoiceCloneItem 
                                    key={voice.id} 
                                    voice={voice} 
                                    onUpdate={(updatedUser) => useStore.setState({ user: updatedUser })}
                                />
                            ))}
                            {(user.custom_voices.length < 5) && (
                                <label className="block w-full py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-center text-xs font-bold rounded-xl transition-all cursor-pointer border border-slate-700">
                                    Weitere Stimme klonen
                                    <input 
                                        type="file" 
                                        accept="audio/*" 
                                        onChange={handleVoiceUpload} 
                                        className="hidden" 
                                        disabled={isCloning}
                                    />
                                </label>
                            )}
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <p className="text-xs text-slate-400 leading-relaxed">
                                Lade eine saubere Sprachaufnahme (MP3/WAV, ca. 30-60 Sek.) hoch, um Deine personalisierte Vorlese-Stimme zu erstellen. Du kannst bis zu 5 Stimmen anlegen.
                            </p>
                            <label className={`block w-full py-3 ${isCloning ? 'bg-slate-800' : 'bg-emerald-500 hover:bg-emerald-400'} text-white text-center font-bold rounded-xl transition-all cursor-pointer shadow-lg shadow-emerald-500/20`}>
                                {isCloning ? (
                                    <span className="flex items-center justify-center gap-2">
                                        <Loader2 className="w-5 h-5 animate-spin" />
                                        Klone Stimme...
                                    </span>
                                ) : (
                                    "Erste Stimme jetzt klonen"
                                )}
                                <input 
                                    type="file" 
                                    accept="audio/*" 
                                    onChange={handleVoiceUpload} 
                                    className="hidden" 
                                    disabled={isCloning}
                                />
                            </label>
                        </div>
                    )}
                </div>
            </div>

            {/* Kindle Integration Section */}
            <div className="w-full glass-panel rounded-3xl p-6 space-y-4">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-orange-500/10 flex items-center justify-center flex-shrink-0">
                        <Download className="w-5 h-5 text-orange-400" />
                    </div>
                    <div>
                        <h3 className="font-bold text-white text-sm">Amazon Kindle™</h3>
                        <p className="text-xs text-slate-400">Direkt auf den E-Reader senden</p>
                    </div>
                </div>

                <div className="flex gap-2">
                    <input
                        type="email"
                        value={kindleEmail}
                        onChange={(e) => setKindleEmail(e.target.value)}
                        placeholder="name@kindle.com"
                        className="flex-1 px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500/50 outline-none transition-all text-white text-sm placeholder:text-slate-600"
                    />
                    <button
                        onClick={handleSaveKindle}
                        disabled={isSavingKindle || kindleEmail === user?.kindle_email}
                        className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2"
                    >
                        {isSavingKindle ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                    </button>
                </div>
                
                <p className="text-xs text-slate-500 leading-relaxed italic">
                    Wichtig: Füge <a href="https://www.amazon.de/hz/mycd/myx#/home/settings/pdoc" target="_blank" rel="noopener noreferrer" className="text-orange-400 hover:underline">"stories@storyja.com"</a> in deinem Amazon-Konto als genehmigte E-Mail hinzu.
                </p>
            </div>

            {/* WhatsApp Integration Section */}
            <div className="w-full glass-panel rounded-3xl p-6 space-y-4 border border-green-500/20">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-green-500/10 flex items-center justify-center flex-shrink-0">
                        <MessageCircle className="w-5 h-5 text-green-400" />
                    </div>
                    <div>
                        <h3 className="font-bold text-white text-sm">WhatsApp Story-Bot</h3>
                        <p className="text-xs text-slate-400">Geschichten per Chat erstellen & verknüpfen</p>
                    </div>
                </div>

                <div className="flex gap-2">
                    <input
                        type="tel"
                        value={whatsappPhone}
                        onChange={(e) => setWhatsappPhone(e.target.value)}
                        placeholder="+49123456789"
                        className="flex-1 px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-green-500/20 focus:border-green-500/50 outline-none transition-all text-white text-sm placeholder:text-slate-600"
                    />
                    <button
                        onClick={handleSaveWhatsapp}
                        disabled={isSavingWhatsapp || whatsappPhone === user?.whatsapp_phone}
                        className="px-4 py-2.5 bg-green-600 hover:bg-green-500 text-white font-medium rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-green-500/20"
                    >
                        {isSavingWhatsapp ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                    </button>
                </div>
                
                <p className="text-xs text-slate-500 leading-relaxed">
                    Verknüpfe deine Nummer, um Geschichten, die du über WhatsApp erstellst, automatisch in deinem Account zu sehen.
                </p>
            </div>

            {/* Alexa Integration Section */}
            <div className={`w-full glass-panel rounded-3xl p-6 space-y-4 border-2 ${user.alexa_user_id ? 'border-sky-500/30' : 'border-transparent'}`}>
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-sky-500/10 flex items-center justify-center flex-shrink-0">
                        <svg className="w-6 h-6 text-sky-400" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm0 22C6.486 22 2 17.514 2 12S6.486 2 12 2s10 4.486 10 10-4.486 10-10 10zm-1.096-15.01c-.503.045-1.002.196-1.428.514-.426.318-.769.756-.991 1.259l-.01.023c-.22.5.244.757.514.514l.023-.01c.218-.184.473-.298.741-.328.268-.03.541.026.786.166.245.14.437.362.548.63.111.268.136.565.07.848-.066.283-.223.535-.443.72-.22.185-.494.288-.778.295-.284.007-.56-.084-.784-.258-.224-.174-.378-.423-.438-.707-.06-.284-.02-.578.113-.836.133-.258.358-.456.63-.563l.023-.008c.5-.22.244-.757-.514-.514l-.01.004c-.5.21-.861.642-1.02 1.15-.159.508-.103 1.054.156 1.52.259.466.69.782 1.2 1.22l.023.018c.27.243.27.757 0 .514l-.023-.018c-.466-.416-.96-.861-1.22-1.12-.26-.259-.413-.59-.441-.951s.053-.717.228-1.022.441-.539.752-.656.657-.107.97-.025.592.261.782.51.272.545.243.839-.144.568-.344.782c-.2.214-.473.344-.766.368-.293.024-.583-.058-.813-.231-.23-.173-.378-.426-.417-.714-.039-.288.026-.58.181-.818.155-.238.4-.396.685-.436l.023-.003c.5-.07.244-.757-.514-.514l-.01.015zM12 4c-4.418 0-8 3.582-8 8s3.582 8 8 8 8-3.582 8-8-3.582-8-8-8zm0 14c-3.309 0-6-2.691-6-6s2.691-6 6-6 6 2.691 6 6-2.691 6-6 6z"/>
                        </svg>
                    </div>
                    <div className="flex-1">
                        <h3 className="font-bold text-white text-sm">Amazon Alexa</h3>
                        <p className="text-xs text-slate-400">
                            {user.alexa_user_id ? 'Konto erfolgreich verknüpft' : 'Geschichten per Sprache anhören'}
                        </p>
                    </div>
                    {user.alexa_user_id && <Check className="w-5 h-5 text-sky-400" />}
                </div>

                {!user.alexa_user_id ? (
                    <button
                        onClick={() => {
                            // Initiation URL for Account Linking from Website (Europe/Pitangui)
                            window.open(`https://pitangui.amazon.com/api/skill/link/M2RQHI40GLJAK9`, '_blank');
                        }}
                        className="w-full py-2.5 bg-sky-500 hover:bg-sky-400 text-sky-950 font-bold rounded-xl transition-all shadow-lg shadow-sky-500/20"
                    >
                        Mit Alexa verbinden
                    </button>
                ) : (
                    <div className="flex flex-col gap-3">
                        <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono bg-slate-900/50 p-2 rounded-lg border border-slate-800">
                             <span className="opacity-50">ID: {user.alexa_user_id.substring(0, 12)}...{user.alexa_user_id.slice(-8)}</span>
                        </div>

                        {/* Playlist Summary */}
                        {playlist.length > 0 && (
                            <div className="bg-slate-900/40 rounded-xl border border-white/5 p-4 space-y-4">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <div className="w-8 h-8 rounded-lg bg-sky-500/10 flex items-center justify-center">
                                            <Music className="w-4 h-4 text-sky-400" />
                                        </div>
                                        <span className="text-xs font-bold text-white uppercase tracking-wider">Warteschlange ({playlist.length})</span>
                                    </div>
                                    <button 
                                        onClick={() => {
                                            if (window.confirm("Möchtest du die gesamte Playlist leeren?")) {
                                                clearPlaylist();
                                                toast.success("Playlist geleert");
                                            }
                                        }}
                                        className="text-[10px] font-bold text-slate-500 hover:text-red-400 transition-colors uppercase tracking-widest"
                                    >
                                        Leeren
                                    </button>
                                </div>
                                
                                <div className="space-y-2 max-h-48 overflow-y-auto pr-2 no-scrollbar">
                                    {playlist.map((story, idx) => (
                                        <div key={story.id} className="flex items-center justify-between group/item py-1">
                                            <div className="flex items-center gap-2 min-w-0">
                                                <span className="text-[10px] font-bold text-slate-600 w-4">{idx + 1}.</span>
                                                <span className="text-xs text-slate-300 truncate font-medium">{story.title}</span>
                                            </div>
                                            <button 
                                                onClick={() => {
                                                    removeFromPlaylist(story.id);
                                                    toast.success("Entfernt");
                                                }}
                                                className="p-1.5 text-slate-600 hover:text-red-400 opacity-0 group-hover/item:opacity-100 transition-all"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <button
                            onClick={handleUnlinkAlexa}
                            className="w-full py-2 bg-slate-800/50 hover:bg-red-500/10 text-slate-400 hover:text-red-400 text-[11px] font-medium rounded-xl transition-all border border-slate-700 hover:border-red-500/20"
                        >
                            Verknüpfung aufheben
                        </button>
                    </div>
                )}
            </div>

            {/* System Settings for Admin */}
            {user?.is_admin && <SystemSettingsSection />}

            {/* Admin Dashboard Area */}
            {user?.is_admin && (
                <div className="w-full glass-panel rounded-3xl p-6 space-y-4 border border-purple-500/20">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center flex-shrink-0">
                            <Shield className="w-5 h-5 text-purple-400" />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-bold text-white text-sm">Adminbereich</h3>
                            <p className="text-xs text-slate-400">Benutzer & Geschichten verwalten</p>
                        </div>
                        <button
                            onClick={() => useStore.getState().setActiveView('admin')}
                            className="px-4 py-2 bg-purple-500 hover:bg-purple-400 text-white text-xs font-bold rounded-xl transition-all shadow-lg shadow-purple-500/20"
                        >
                            Öffnen
                        </button>
                    </div>
                </div>
            )}

            {/* RSS Feed Section */}
            {user?.is_admin && (
                <div className="w-full glass-panel rounded-3xl p-6 space-y-4">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                            <Radio className="w-5 h-5 text-emerald-400" />
                        </div>
                        <div>
                            <h3 className="font-bold text-white text-sm">Podcast-Feed</h3>
                            <p className="text-xs text-slate-400">Abonniere in Spotify oder Apple Podcasts</p>
                        </div>
                    </div>

                    <div className="flex gap-2">
                        <input
                            type="text"
                            readOnly
                            value={rssUrl}
                            className="flex-1 px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-xs text-slate-400 outline-none"
                        />
                        <button
                            onClick={copyToClipboard}
                            className="px-4 py-2.5 bg-white/5 hover:bg-white/10 text-slate-300 font-medium rounded-xl transition-colors flex items-center gap-2 border border-white/5"
                        >
                            <Copy className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            )}
            </>
            )}

            {/* Logout */}
            <div className="w-full pt-4">
                <button
                    onClick={() => {
                        if (isGuest) {
                            if (window.confirm("Achtung! Als Gast gehen deine Geschichten beim Abmelden verloren. Möchtest du dich wirklich abmelden?")) {
                                logout();
                            }
                        } else {
                            logout();
                        }
                    }}
                    className="w-full flex items-center justify-center gap-2 py-3.5 text-red-400 font-bold bg-red-500/5 border border-red-500/10 hover:bg-red-500/10 rounded-2xl transition-all"
                >
                    <LogOut className="w-5 h-5" />
                    Abmelden
                </button>
            </div>

            {showAvatarUpload && (
                <ProfilePictureUpload 
                    onUpload={handleAvatarUpload}
                    onClose={() => setShowAvatarUpload(false)}
                />
            )}
        </div>
    );
}

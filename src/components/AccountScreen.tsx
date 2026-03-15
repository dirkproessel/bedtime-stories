import { useState } from 'react';
import { useStore } from '../store/useStore';
import { LogOut, Download, Mail, Check, Loader2, Radio, Copy, User, Shield } from 'lucide-react';
import { updateKindleEmail, updateUsername } from '../lib/api';
import toast from 'react-hot-toast';

export default function AccountScreen() {
    const { user, logout } = useStore();
    const [kindleEmail, setKindleEmail] = useState(user?.kindle_email || '');
    const [username, setUsername] = useState(user?.username || user?.email || '');
    const [isSavingKindle, setIsSavingKindle] = useState(false);
    const [isSavingUsername, setIsSavingUsername] = useState(false);

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

    const rssUrl = `${window.location.protocol}//${window.location.host.replace(':5173', ':8000')}/api/feed/${user?.id}.xml`;
    const copyToClipboard = () => {
        navigator.clipboard.writeText(rssUrl);
        toast.success('RSS-Link kopiert!');
    };

    if (!user) return null;

    return (
        <div className="flex flex-col items-center max-w-lg mx-auto p-6 md:p-12 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-32">
            
            {/* Profile Header */}
            <div className="w-full text-center space-y-2">
                <div className="relative inline-block">
                    <div className="w-24 h-24 rounded-full bg-emerald-500/10 border-2 border-emerald-500/20 flex items-center justify-center mx-auto mb-4">
                        <User className="w-12 h-12 text-emerald-500" />
                    </div>
                    {user.is_admin && (
                        <div className="absolute -top-1 -right-1 bg-emerald-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 shadow-lg border border-emerald-400">
                            <Shield className="w-3 h-3" />
                            ADMIN
                        </div>
                    )}
                </div>
                <h2 className="text-2xl font-serif font-bold text-white tracking-tight">
                    {user.username || 'Dein Profil'}
                </h2>
                <div className="flex items-center justify-center gap-2 text-slate-400 text-sm">
                    <Mail className="w-4 h-4" />
                    <span>{user.email}</span>
                </div>
            </div>

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
                
                <p className="text-[10px] text-slate-500 leading-relaxed italic">
                    Wichtig: Füge "{user.email}" in deinem Amazon-Konto als genehmigte E-Mail hinzu.
                </p>
            </div>

            {/* RSS Feed Section */}
            {user?.is_admin && (
                <div className="w-full glass-panel rounded-3xl p-6 space-y-4">
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
                            className="flex-1 px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-[10px] font-mono text-slate-400 outline-none"
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

            {/* Logout */}
            <div className="w-full pt-4">
                <button
                    onClick={logout}
                    className="w-full flex items-center justify-center gap-2 py-3.5 text-red-400 font-bold bg-red-500/5 border border-red-500/10 hover:bg-red-500/10 rounded-2xl transition-all"
                >
                    <LogOut className="w-5 h-5" />
                    Abmelden
                </button>
            </div>
        </div>
    );
}

import { useState } from 'react';
import { useStore } from '../store/useStore';
import { LogOut, Download, Mail, Check, Loader2, Radio, Copy, User, Shield, Camera } from 'lucide-react';
import { updateKindleEmail, updateUsername, uploadProfilePicture } from '../lib/api';
import toast from 'react-hot-toast';
import ProfilePictureUpload from './ProfilePictureUpload';

export default function AccountScreen() {
    const { user, logout } = useStore();
    const [kindleEmail, setKindleEmail] = useState(user?.kindle_email || '');
    const [username, setUsername] = useState(user?.username || user?.email || '');
    const [isSavingKindle, setIsSavingKindle] = useState(false);
    const [isSavingUsername, setIsSavingUsername] = useState(false);
    const [showAvatarUpload, setShowAvatarUpload] = useState(false);

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
                
                <p className="text-xs text-slate-500 leading-relaxed italic">
                    Wichtig: Füge <a href="https://www.amazon.de/hz/mycd/myx#/home/settings/pdoc" target="_blank" rel="noopener noreferrer" className="text-orange-400 hover:underline">"stories@storyja.com"</a> in deinem Amazon-Konto als genehmigte E-Mail hinzu.
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
                    <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                         <span className="opacity-50">ID: {user.alexa_user_id.substring(0, 12)}...{user.alexa_user_id.slice(-8)}</span>
                    </div>
                )}
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

            {showAvatarUpload && (
                <ProfilePictureUpload 
                    onUpload={handleAvatarUpload}
                    onClose={() => setShowAvatarUpload(false)}
                />
            )}
        </div>
    );
}

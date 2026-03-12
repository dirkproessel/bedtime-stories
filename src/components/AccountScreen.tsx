import { useState } from 'react';
import { useStore } from '../store/useStore';
import { User, LogOut, Download, Mail, Check, Loader2, Radio, Copy } from 'lucide-react';
import { updateKindleEmail } from '../lib/api';
import toast from 'react-hot-toast';

export default function AccountScreen() {
    const { user, logout } = useStore();
    const [kindleEmail, setKindleEmail] = useState(user?.kindle_email || '');
    const [isSaving, setIsSaving] = useState(false);

    const handleSaveKindle = async () => {
        if (kindleEmail === user?.kindle_email) return;
        setIsSaving(true);
        try {
            await updateKindleEmail(kindleEmail);
            toast.success('Kindle-Adresse gespeichert!');
            // Update local user state
            useStore.setState({ user: { ...user!, kindle_email: kindleEmail } });
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Speichern');
        } finally {
            setIsSaving(false);
        }
    };

    const rssUrl = `${window.location.protocol}//${window.location.host.replace(':5173', ':8000')}/api/feed/${user?.id}.xml`;
    const copyToClipboard = () => {
        navigator.clipboard.writeText(rssUrl);
        toast.success('RSS-Link kopiert!');
    };

    if (!user) return null;

    return (
        <div className="flex flex-col items-center max-w-lg mx-auto p-6 md:p-12 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Header */}
            <div className="flex flex-col items-center mb-8">
        <div className="w-24 h-24 bg-indigo-100 rounded-full flex items-center justify-center mb-4">
          <User className="w-12 h-12 text-indigo-500" />
        </div>
        <h2 className="text-3xl font-bold text-slate-900 mb-1">Mein Konto</h2>
        <p className="text-slate-500 font-medium">
          {user ? user.email : 'Gastzugriff'}
        </p>
        {user?.is_admin && (
          <span className="mt-3 px-3 py-1 bg-amber-100 text-amber-700 text-xs font-bold rounded-full uppercase tracking-wider">
            Admin
          </span>
        )}
        {!user && (
          <span className="mt-3 px-3 py-1 bg-slate-100 text-slate-500 text-xs font-bold rounded-full uppercase tracking-wider">
            Eingeschränkt
          </span>
        )}
      </div>
            {/* Kindle Integration Section */}
            <div className="w-full bg-white rounded-3xl p-6 shadow-sm border border-slate-100 space-y-6">
                <div className="flex items-center gap-4 border-b border-slate-100 pb-4">
                    <div className="w-12 h-12 rounded-xl bg-orange-100 flex items-center justify-center flex-shrink-0">
                        <Download className="w-6 h-6 text-orange-500" />
                    </div>
                    <div>
                        <h3 className="font-bold text-slate-800">Amazon Kindle™</h3>
                        <p className="text-sm text-slate-500 leading-tight">
                            Sende generierte Geschichten direkt auf deinen E-Reader.
                        </p>
                    </div>
                </div>

                <div className="space-y-4">
                    <div className="space-y-2">
                        <label className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                            <Mail className="w-4 h-4" />
                            Kindle E-Mail Adresse
                        </label>
                        <div className="flex gap-2">
                            <input
                                type="email"
                                value={kindleEmail}
                                onChange={(e) => setKindleEmail(e.target.value)}
                                placeholder="name@kindle.com"
                                className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-100 focus:border-indigo-400 outline-none transition-all placeholder:text-slate-400"
                            />
                            <button
                                onClick={handleSaveKindle}
                                disabled={isSaving || kindleEmail === user?.kindle_email}
                                className="px-4 py-3 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-xl transition-colors disabled:opacity-50 disabled:hover:bg-slate-800 flex items-center gap-2"
                            >
                                {isSaving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Check className="w-5 h-5" />}
                            </button>
                        </div>
                        <p className="text-xs text-slate-400">
                            Füge zuerst "dirk.proessel@gmail.com" zu deinen genehmigten Email-Adressen bei Amazon hinzu.
                        </p>
                    </div>
                </div>
            </div>

            {/* RSS Feed Section */}
            <div className="w-full bg-white rounded-3xl p-6 shadow-sm border border-slate-100 space-y-6">
                <div className="flex items-center gap-4 border-b border-slate-100 pb-4">
                    <div className="w-12 h-12 rounded-xl bg-indigo-100 flex items-center justify-center flex-shrink-0">
                        <Radio className="w-6 h-6 text-indigo-500" />
                    </div>
                    <div>
                        <h3 className="font-bold text-slate-800">Persönlicher Podcast-Feed</h3>
                        <p className="text-sm text-slate-500 leading-tight">
                            Abonniere deine Geschichten in Spotify oder Apple Podcasts.
                        </p>
                    </div>
                </div>

                <div className="space-y-4">
                    <div className="space-y-2">
                        <label className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                            RSS URL
                        </label>
                        <div className="flex gap-2">
                            <input
                                type="text"
                                readOnly
                                value={rssUrl}
                                className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono text-slate-500 outline-none"
                            />
                            <button
                                onClick={copyToClipboard}
                                className="px-4 py-3 bg-slate-100 hover:bg-slate-200 text-slate-600 font-medium rounded-xl transition-colors flex items-center gap-2"
                            >
                                <Copy className="w-5 h-5" />
                            </button>
                        </div>
                        <p className="text-[10px] text-slate-400">
                            Dieser Link ist privat. Teile ihn nur mit Personen, die Zugriff auf deine Geschichten haben sollen.
                        </p>
                    </div>
                </div>
            </div>

            {/* Danger Zone */}
            <div className="w-full pt-8">
                <button
                    onClick={logout}
                    className="w-full flex items-center justify-center gap-2 py-4 text-red-500 font-bold bg-red-50 hover:bg-red-100 rounded-2xl transition-colors"
                >
                    <LogOut className="w-5 h-5" />
                    Abmelden
                </button>
            </div>
        </div>
    );
}

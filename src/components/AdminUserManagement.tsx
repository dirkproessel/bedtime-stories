import { useEffect } from 'react';
import { useStore } from '../store/useStore';
import { Trash2, Shield, User, Mail, Calendar, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

export default function AdminUserManagement() {
    const { adminUsers, loadAdminUsers, deleteAdminUser, updateAdminUser, isLoading } = useStore();

    useEffect(() => {
        loadAdminUsers();
    }, [loadAdminUsers]);

    const handleDelete = async (id: string, email: string) => {
        if (!confirm(`Benutzer ${email} wirklich löschen?`)) return;
        try {
            await deleteAdminUser(id);
            toast.success('Benutzer gelöscht');
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Löschen');
        }
    };

    const handleToggleAdmin = async (id: string, currentStatus: boolean) => {
        try {
            await updateAdminUser(id, { is_admin: !currentStatus });
            toast.success('Status aktualisiert');
        } catch (e: any) {
            toast.error(e.message || 'Fehler beim Aktualisieren');
        }
    };

    if (isLoading && adminUsers.length === 0) {
        return (
            <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {adminUsers.map((user) => (
                <div key={user.id} className="glass-panel rounded-2xl p-4 flex items-center justify-between group">
                    <div className="flex items-center gap-4">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${user.is_admin ? 'bg-emerald-500/20 text-emerald-500' : 'bg-white/5 text-slate-400'}`}>
                            {user.is_admin ? <Shield className="w-5 h-5" /> : <User className="w-5 h-5" />}
                        </div>
                        <div className="flex flex-col">
                            <span className="text-white font-medium flex items-center gap-2">
                                {user.username || user.email}
                                {user.is_admin && <span className="text-[10px] bg-emerald-500 text-white px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">Admin</span>}
                            </span>
                            <div className="flex items-center gap-3 text-xs text-slate-500">
                                <span className="flex items-center gap-1"><Mail className="w-3 h-3" /> {user.email}</span>
                                <span className="flex items-center gap-1"><Calendar className="w-3 h-3" /> {new Date(user.created_at).toLocaleDateString('de-DE')}</span>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                            onClick={() => handleToggleAdmin(user.id, user.is_admin)}
                            className="p-2 text-slate-400 hover:text-emerald-500 hover:bg-emerald-500/10 rounded-lg transition-all"
                            title={user.is_admin ? "Admin-Rechte entziehen" : "Zum Admin machen"}
                        >
                            <Shield className="w-5 h-5" />
                        </button>
                        <button
                            onClick={() => handleDelete(user.id, user.email)}
                            className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-all"
                            title="Benutzer löschen"
                        >
                            <Trash2 className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            ))}

            {adminUsers.length === 0 && !isLoading && (
                <div className="text-center py-12 text-slate-500 italic">
                    Keine Benutzer gefunden.
                </div>
            )}
        </div>
    );
}

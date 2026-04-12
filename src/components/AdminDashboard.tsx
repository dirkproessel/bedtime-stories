import { useState } from 'react';
import { useStore } from '../store/useStore';
import { Users, BookOpen, ChevronLeft, Mic } from 'lucide-react';
import AdminUserManagement from './AdminUserManagement';
import AdminStoryManagement from './AdminStoryManagement';
import AdminVoiceManagement from './AdminVoiceManagement';

export default function AdminDashboard() {
    const { setActiveView } = useStore();
    const [subView, setSubView] = useState<'users' | 'stories' | 'voices'>('users');
    const [filterUserId, setFilterUserId] = useState<string | null>(null);

    const handleShowUserStories = (userId: string) => {
        setFilterUserId(userId);
        setSubView('stories');
    };

    return (
        <div className="flex flex-col max-w-4xl mx-auto p-4 md:p-8 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-32">
            
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <button 
                    onClick={() => setActiveView('profile')}
                    className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors text-sm"
                >
                    <ChevronLeft className="w-4 h-4" />
                    Zurück zum Profil
                </button>
                <h1 className="text-2xl font-bold text-white">Adminbereich</h1>
                <div className="w-20"></div> {/* Spacer */}
            </div>

            {/* Sub-Navigation Tabs */}
            <div className="flex gap-2 p-1 bg-white/5 rounded-2xl border border-white/10 self-center">
                <button
                    onClick={() => {
                        setSubView('users');
                        setFilterUserId(null); // Clear filter when going back to user list
                    }}
                    className={`flex items-center gap-2 px-6 py-2.5 rounded-xl transition-all font-medium text-sm ${
                        subView === 'users' 
                        ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/20' 
                        : 'text-slate-400 hover:text-white hover:bg-white/5'
                    }`}
                >
                    <Users className="w-4 h-4" />
                    Benutzer
                </button>
                <button
                    onClick={() => setSubView('stories')}
                    className={`flex items-center gap-2 px-6 py-2.5 rounded-xl transition-all font-medium text-sm ${
                        subView === 'stories' 
                        ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/20' 
                        : 'text-slate-400 hover:text-white hover:bg-white/5'
                    }`}
                >
                    <BookOpen className="w-4 h-4" />
                    Geschichten
                </button>
                <button
                    onClick={() => setSubView('voices')}
                    className={`flex items-center gap-2 px-6 py-2.5 rounded-xl transition-all font-medium text-sm ${
                        subView === 'voices' 
                        ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/20' 
                        : 'text-slate-400 hover:text-white hover:bg-white/5'
                    }`}
                >
                    <Mic className="w-4 h-4" />
                    Stimmen
                </button>
            </div>

            {/* Content Area */}
            <div className="w-full">
                {subView === 'users' ? (
                    <AdminUserManagement onShowStories={handleShowUserStories} />
                ) : subView === 'stories' ? (
                    <AdminStoryManagement 
                        filterUserId={filterUserId} 
                        onClearFilter={() => setFilterUserId(null)} 
                    />
                ) : (
                    <AdminVoiceManagement />
                )}
            </div>
        </div>
    );
}

import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { Mail, Lock, Loader2 } from 'lucide-react';

export default function LoginScreen() {
    const { login, register, isLoading, error } = useStore();
    const [isLoginMode, setIsLoginMode] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [localError, setLocalError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLocalError(null);

        if (!email || !password) {
            setLocalError('Bitte fülle alle Felder aus.');
            return;
        }

        try {
            if (isLoginMode) {
                await login(email, password);
            } else {
                await register(email, password);
            }
        } catch (err: any) {
            // Error is already handled/set in the store, but we can catch it here if we want local UI effects
        }
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-[80vh] px-6">
            <p className="text-slate-400 mb-8 text-center max-w-sm">
                {isLoginMode 
                    ? 'Logge dich ein, um deine Bibliothek zu durchforsten und neue literarische Experimente zu starten.' 
                    : 'Registriere dich, um neue literarische Experimente zu starten.'}
            </p>

            <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4">
                {(error || localError) && (
                    <div className="p-3 rounded-xl bg-red-50 text-red-600 text-sm font-medium text-center border border-red-100">
                        {localError || error}
                    </div>
                )}
                
                <div className="relative">
                    <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                        <Mail className="w-5 h-5 text-slate-400" />
                    </div>
                    <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="E-Mail Adresse"
                        className="w-full pl-12 pr-4 py-3.5 bg-slate-900/50 border border-slate-800 rounded-2xl focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all placeholder:text-slate-600 font-medium text-text"
                        required
                    />
                </div>

                <div className="relative">
                    <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                        <Lock className="w-5 h-5 text-slate-400" />
                    </div>
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Passwort"
                        className="w-full pl-12 pr-4 py-3.5 bg-slate-900/50 border border-slate-800 rounded-2xl focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all placeholder:text-slate-600 font-medium text-text"
                        required
                    />
                </div>

                <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full flex items-center justify-center gap-2 py-3.5 bg-[#2D5A4C] hover:bg-[#1A4336] text-white font-bold rounded-2xl shadow-lg shadow-[#2D5A4C]/15 transition-all active:scale-[0.98] disabled:opacity-70"
                >
                    {isLoading ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                        isLoginMode ? 'Anmelden' : 'Konto erstellen'
                    )}
                </button>
            </form>

            <div className="mt-6 flex flex-col items-center gap-4">
                <button 
                    onClick={() => {
                        const newMode = !isLoginMode;
                        setIsLoginMode(newMode);
                        localStorage.setItem('is_registering', (!newMode).toString());
                    }}
                    className="text-sm font-medium text-slate-500 hover:text-[#2D5A4C] transition-colors"
                >
                    {isLoginMode 
                        ? 'Noch kein Konto? Hier registrieren.' 
                        : 'Bereits ein Konto? Hier anmelden.'}
                </button>

                <div className="w-12 h-px bg-slate-100" />

                <button 
                    onClick={() => {
                        const { setActiveView } = useStore.getState();
                        setActiveView('create');
                    }}
                    className="text-sm font-bold text-[#2D5A4C] hover:text-[#1A4336] transition-colors"
                >
                    Als Gast fortfahren
                </button>
            </div>
        </div>
    );
}

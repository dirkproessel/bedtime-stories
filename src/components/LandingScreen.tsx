import React, { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { Sparkles, Headphones, Library, Mail, Lock, Loader2, Play } from 'lucide-react';
import { fetchStories, getThumbUrl, StoryMeta } from '../lib/api';

export default function LandingScreen() {
    const { login, register, isLoading, error, setActiveView, setReaderOpen } = useStore();
    const [publicStories, setPublicStories] = useState<StoryMeta[]>([]);
    
    // Auth State (Focus on Registration)
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [localError, setLocalError] = useState<string | null>(null);

    useEffect(() => {
        // Fetch last 3 public stories independently of global store
        fetchStories({ page: 1, pageSize: 3, filter: 'public' })
            .then(res => setPublicStories(res.stories))
            .catch(console.error);
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLocalError(null);

        if (!email || !password) {
            setLocalError('Bitte fülle alle Felder aus.');
            return;
        }

        try {
            // Focus is registration. Try to register first.
            await register(email, password);
            setActiveView('create');
        } catch (err: any) {
            // If already registered (usually "Email already registered" or 400)
            if (err.message && (err.message.toLowerCase().includes('already') || err.message.toLowerCase().includes('existiert') || err.message.toLowerCase().includes('registriert'))) {
                setLocalError('Konto existiert bereits. Bitte logge dich unten ein.');
            } else {
                setLocalError(err.message || 'Ein Fehler ist aufgetreten.');
            }
        }
    };

    const handleLoginSwitch = () => {
        localStorage.setItem('is_registering', 'false');
        setActiveView('login');
    };

    return (
        <div className="flex flex-col w-full min-h-screen text-text font-sans">
            
            {/* Hero Section */}
            <section className="relative w-full min-h-[85vh] sm:min-h-[70vh] flex flex-col justify-center items-center px-6 pt-12 pb-24 overflow-hidden rounded-b-[3rem] sm:rounded-b-[4rem] border-b border-slate-800/50">
                {/* Background Image & Gradient */}
                <div className="absolute inset-0 z-0">
                    <img 
                        src="/hero_bg.png" 
                        alt="Hero Background" 
                        className="w-full h-full object-cover opacity-60"
                    />
                    <div className="absolute inset-0 bg-gradient-to-b from-[#0B1215]/40 via-[#0B1215]/80 to-[#0B1215]" />
                </div>

                <div className="relative z-10 flex flex-col items-center text-center max-w-2xl mt-12 sm:mt-0">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-md mb-6">
                        <Sparkles className="w-4 h-4 text-primary" />
                        <span className="text-xs font-medium tracking-wider uppercase text-slate-300">Dein KI-Literatur-Labor</span>
                    </div>
                    
                    <h1 className="text-4xl sm:text-6xl font-bold tracking-tight leading-[1.1] mb-6 text-white text-balance drop-shadow-2xl">
                        Deine Idee. <br className="sm:hidden" />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-teal-400">Deine Story.</span> <br />
                        Auf Knopfdruck.
                    </h1>
                    
                    <p className="text-base sm:text-lg text-slate-300 mb-10 text-balance leading-relaxed max-w-lg">
                        Erschaffe einzigartige Kurzgeschichten, lass sie dir von lebensechten KI-Stimmen vorlesen und tauche in faszinierende neue Welten ein.
                    </p>
                    
                    <div className="flex flex-col sm:flex-row w-full sm:w-auto gap-4">
                        <button 
                            onClick={() => document.getElementById('auth-section')?.scrollIntoView({ behavior: 'smooth' })}
                            className="w-full sm:w-auto px-8 py-4 bg-primary hover:bg-primary/90 text-white font-bold rounded-2xl shadow-lg shadow-primary/25 transition-all active:scale-[0.98] text-lg flex items-center justify-center gap-2"
                        >
                            Jetzt kostenlos starten
                        </button>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="px-6 py-20 w-full max-w-5xl mx-auto">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-surface border border-slate-800/50 rounded-3xl p-6 sm:p-8 flex flex-col gap-4">
                        <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center border border-primary/20">
                            <Sparkles className="w-6 h-6 text-primary" />
                        </div>
                        <h3 className="text-xl font-bold text-white">KI-Magie</h3>
                        <p className="text-slate-400 text-sm leading-relaxed">
                            Aus einem kurzen Gedanken wird ein fesselndes Abenteuer. Du bestimmst das Genre, die KI schreibt die Story.
                        </p>
                    </div>
                    <div className="bg-surface border border-slate-800/50 rounded-3xl p-6 sm:p-8 flex flex-col gap-4">
                        <div className="w-12 h-12 rounded-2xl bg-teal-500/10 flex items-center justify-center border border-teal-500/20">
                            <Headphones className="w-6 h-6 text-teal-500" />
                        </div>
                        <h3 className="text-xl font-bold text-white">Audio-Erlebnis</h3>
                        <p className="text-slate-400 text-sm leading-relaxed">
                            Lehn dich zurück. Professionelle, lebensechte KI-Stimmen vertonen deine Geschichte in Hörbuch-Qualität.
                        </p>
                    </div>
                    <div className="bg-surface border border-slate-800/50 rounded-3xl p-6 sm:p-8 flex flex-col gap-4">
                        <div className="w-12 h-12 rounded-2xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20">
                            <Library className="w-6 h-6 text-purple-500" />
                        </div>
                        <h3 className="text-xl font-bold text-white">Deine Bibliothek</h3>
                        <p className="text-slate-400 text-sm leading-relaxed">
                            Sammle deine Meisterwerke, teile sie mit Freunden oder lausche ihnen abends gemütlich beim Einschlafen.
                        </p>
                    </div>
                </div>
            </section>

            {/* Showcase Section */}
            {publicStories.length > 0 && (
                <section className="px-6 py-12 w-full max-w-5xl mx-auto">
                    <div className="text-center mb-10">
                        <h2 className="text-3xl font-bold text-white mb-3">Lass dich inspirieren</h2>
                        <p className="text-slate-400">Hör dir an, was mit dem Kurzgeschichten-Labor möglich ist.</p>
                    </div>
                    <div className="flex overflow-x-auto gap-4 pb-8 snap-x snap-mandatory hide-scrollbar -mx-6 px-6 sm:mx-0 sm:px-0 sm:grid sm:grid-cols-3">
                        {publicStories.map(story => (
                            <div 
                                key={story.id} 
                                className="snap-center shrink-0 w-[280px] sm:w-auto relative group rounded-3xl overflow-hidden bg-surface border border-slate-800/50 cursor-pointer transition-transform hover:scale-[1.02]"
                                onClick={() => setReaderOpen(true, story.id)}
                            >
                                <div className="aspect-square w-full relative">
                                    <img 
                                        src={getThumbUrl(story.id)} 
                                        alt={story.title}
                                        className="w-full h-full object-cover"
                                        loading="lazy"
                                    />
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
                                    
                                    <div className="absolute top-3 left-3 bg-black/60 backdrop-blur-md px-3 py-1 rounded-full border border-white/10">
                                        <span className="text-[10px] font-medium tracking-wider uppercase text-slate-200">{story.genre}</span>
                                    </div>

                                    <div className="absolute bottom-4 left-4 right-4">
                                        <h3 className="text-lg font-bold text-white leading-tight mb-1 drop-shadow-md line-clamp-2">{story.title}</h3>
                                        <div className="flex items-center gap-2">
                                            <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center">
                                                <Play className="w-3 h-3 text-white fill-current ml-0.5" />
                                            </div>
                                            <span className="text-xs font-medium text-slate-300">Reinhören</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            )}

            {/* Auth Section */}
            <section id="auth-section" className="px-6 py-20 w-full max-w-md mx-auto flex flex-col items-center">
                <div className="w-full bg-surface border border-slate-800/50 rounded-[2.5rem] p-8 sm:p-10 shadow-2xl relative overflow-hidden">
                    <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent" />
                    
                    <div className="text-center mb-8">
                        <h2 className="text-2xl font-bold text-white mb-2">Dein Labor wartet</h2>
                        <p className="text-sm text-slate-400">Erstelle in Sekunden ein kostenloses Konto und beginne deine erste Story.</p>
                    </div>

                    <form onSubmit={handleSubmit} className="w-full space-y-4">
                        {(error || localError) && (
                            <div className="p-4 rounded-2xl bg-red-500/10 text-red-400 text-sm font-medium text-center border border-red-500/20">
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
                                className="w-full pl-12 pr-4 py-4 bg-[#0B1215] border border-slate-800 rounded-2xl focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all placeholder:text-slate-600 font-medium text-text"
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
                                placeholder="Passwort wählen"
                                className="w-full pl-12 pr-4 py-4 bg-[#0B1215] border border-slate-800 rounded-2xl focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all placeholder:text-slate-600 font-medium text-text"
                                required
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full flex items-center justify-center gap-2 py-4 mt-2 bg-primary hover:bg-primary/90 text-white font-bold rounded-2xl shadow-lg shadow-primary/20 transition-all active:scale-[0.98] disabled:opacity-70"
                        >
                            {isLoading ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                'Kostenlos registrieren'
                            )}
                        </button>
                    </form>

                    <div className="mt-8 flex flex-col items-center gap-5">
                        <div className="h-px w-16 bg-slate-800" />
                        <p className="text-sm text-slate-400">
                            Bereits registriert?{' '}
                            <button 
                                onClick={handleLoginSwitch}
                                className="font-bold text-primary hover:text-primary/80 transition-colors"
                            >
                                Hier einloggen
                            </button>
                        </p>
                    </div>
                </div>
            </section>
            
            {/* Minimal Footer Spacer for bottom navigation */}
            <div className="h-32 lg:h-12 w-full" />
        </div>
    );
}

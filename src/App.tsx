import { useEffect } from 'react';
import { useStore } from './store/useStore';
import { PenTool, BookOpen, User, Compass } from 'lucide-react';
import { Toaster } from 'react-hot-toast';
import StoryCreator from './components/StoryCreator';
import StoryArchive from './components/StoryArchive';
import LoginScreen from './components/LoginScreen';
import AccountScreen from './components/AccountScreen';
import ReaderLayer from './components/ReaderLayer';
import AudioCompanion from './components/AudioCompanion';
import AdminDashboard from './components/AdminDashboard';

const NAV_ITEMS = [
  { key: 'create' as const, label: 'Erschaffen', icon: PenTool },
  { key: 'library' as const, label: 'Bibliothek', icon: BookOpen },
  { key: 'discover' as const, label: 'Entdecken', icon: Compass },
  { key: 'profile' as const, label: 'Profil', icon: User },
];

function App() {
  const { fetchData, isLoading, error, isInitialized, activeView, setActiveView, user, token } = useStore();

  // Initial Data Fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (isInitialized && !user && !token && activeView === 'profile') {
        setActiveView('login');
    }
  }, [isInitialized, user, token, activeView, setActiveView]);

  // Sync URL Hash -> Store State (Listeners for Back/Forward & direct link access)
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '');
      const path = window.location.pathname;

      // 1. Check Hash for story (standard case)
      const lowerHash = hash.toLowerCase();
      if (lowerHash.startsWith('/story/') || lowerHash.startsWith('/player/')) {
        const storyId = hash.split('/')[2];
        if (storyId) {
          useStore.getState().setReaderOpen(true, storyId);
          return;
        }
      }

      // 2. Check Pathname for story (robustness for stripped hashes/SEO links)
      const lowerPath = path.toLowerCase();
      if (lowerPath.startsWith('/story/') || lowerPath.startsWith('/player/')) {
        const storyId = path.split('/')[2];
        if (storyId) {
          useStore.getState().setReaderOpen(true, storyId);
          return;
        }
      }

      // If hash is not a story hash but reader is open, close it (e.g. via browser back)
      if (useStore.getState().isReaderOpen) {
        useStore.getState().setReaderOpen(false);
      }

      // If we are definitely not logged in, don't change other routes
      if (!localStorage.getItem('auth_token')) return;

      if (hash === '/library') {
        setActiveView('library');
        return;
      }

      if (hash === '/discover') {
        setActiveView('discover');
        return;
      }

      if (hash === '/profile') {
        setActiveView('profile');
        return;
      }

      if (hash === '/admin') {
        setActiveView('admin');
        return;
      }

      if (hash === '/create' || hash === '') {
        setActiveView('create');
        return;
      }
    };

    // Run once on load
    handleHashChange();

    window.addEventListener('hashchange', handleHashChange);
    window.addEventListener('popstate', handleHashChange); // Handle pushState/pathname changes
    return () => {
      window.removeEventListener('hashchange', handleHashChange);
      window.removeEventListener('popstate', handleHashChange);
    };
  }, [setActiveView]);

  // Sync Store State -> URL Hash
  useEffect(() => {
    let desiredHash = '';
    const { isReaderOpen, readerStoryId } = useStore.getState();

    if (isReaderOpen && readerStoryId) {
      desiredHash = `#/Story/${readerStoryId}`;
    } else if (activeView === 'library') {
      desiredHash = `#/library`;
    } else if (activeView === 'discover') {
      desiredHash = `#/discover`;
    } else if (activeView === 'create') {
      desiredHash = `#/create`;
    } else if (activeView === 'profile') {
      desiredHash = `#/profile`;
    } else if (activeView === 'admin') {
      desiredHash = `#/admin`;
    } else if (activeView === 'login') {
      desiredHash = ``;
    }

    if (desiredHash !== '' && window.location.hash !== desiredHash) {
      window.history.pushState(null, '', desiredHash);
    }
  }, [activeView, useStore.getState().isReaderOpen, useStore.getState().readerStoryId]);

  if (isLoading && !isInitialized) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center w-full gap-8">
        <div className="relative">
          <div className="w-24 h-24 flex items-center justify-center animate-pulse">
            <img src="/logo.png" alt="Logo" className="w-20 h-20 object-contain" />
          </div>
          <div className="absolute bottom-2 right-2 w-4 h-4 bg-primary rounded-full border-2 border-background shadow-[0_0_15px_rgba(34,197,94,0.3)]" />
        </div>
        <div className="flex flex-col items-center gap-3">
          <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-400 font-medium tracking-widest">Labor wird vorbereitet</span>
          <div className="w-32 h-1 bg-slate-100 rounded-full overflow-hidden relative">
            <div className="absolute inset-0 bg-[#2D5A4C] w-1/3 rounded-full animate-shimmer" />
          </div>
        </div>
      </div>
    );
  }


  if (error && activeView !== 'login') {
    return (
      <div className="min-h-screen bg-[#F8F9FA] flex flex-col items-center justify-center w-full p-6 text-center">
        <div className="w-16 h-16 bg-red-100 text-red-500 rounded-2xl flex items-center justify-center mb-4 text-2xl font-bold">!</div>
        <h2 className="text-xl font-serif font-bold text-[#1A1C1E] mb-2">Verbindungsfehler</h2>
        <p className="text-[#6B7280] text-sm mb-6 font-mono text-[11px] uppercase tracking-wider">{error}</p>
        <button onClick={() => fetchData()} className="btn-primary px-8">
          Erneut versuchen
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col w-full relative overflow-hidden">
      {/* Global Brand Header */}
      <header className="pt-2 px-4 pb-1 max-w-2xl mx-auto w-full flex flex-row items-center justify-center gap-3 sm:gap-5 text-left">
        <div className="shrink-0 mt-1">
          <img src="/logo.png" alt="Logo" className="w-18 h-18 sm:w-22 sm:h-22 object-contain" />
        </div>
        <div className="flex flex-col">
          <h2 className="text-xl sm:text-2xl font-semibold text-text mb-0.5 font-serif tracking-tight leading-tight">Kurzgeschichten-Labor</h2>
          <p className="text-[11px] tracking-widest uppercase text-text-muted opacity-80 font-mono">
            Literatur auf Knopfdruck
          </p>
        </div>
      </header>

      {/* Dynamic Page Title */}
      <div className="px-6 pb-2 max-w-2xl mx-auto w-full text-center">
        <h1 className="text-lg font-bold text-text-muted/80 font-serif italic">
          {activeView === 'create' && 'Erschaffe eine eigene Geschichte'}
          {activeView === 'library' && 'Meine Bibliothek'}
          {activeView === 'discover' && 'Entdecke neue Geschichten'}
          {activeView === 'profile' && 'Mein Profil'}
          {activeView === 'admin' && 'Adminbereich'}
          {activeView === 'login' && (localStorage.getItem('is_registering') === 'true' ? 'Konto erstellen' : 'Willkommen zurück')}
        </h1>
      </div>

      {/* Reader Layer (z-40) */}
      <ReaderLayer />

      <Toaster 
        position="top-center" 
        toastOptions={{
          duration: 3000,
          style: {
            background: 'rgba(23, 32, 35, 0.95)',
            color: '#E2E8F0',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            border: '1px solid rgba(34, 197, 94, 0.2)',
            borderRadius: '1.25rem',
            fontSize: '14px',
            fontWeight: '500',
            padding: '12px 20px',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
          },
          success: {
            iconTheme: {
              primary: '#22C55E',
              secondary: '#FFFFFF',
            },
          },
          error: {
            iconTheme: {
              primary: '#EF4444',
              secondary: '#FFFFFF',
            },
            style: {
              border: '1px solid rgba(239, 68, 68, 0.2)',
            }
          },
        }}
      />
      <main id="main-scroll-container" className="flex-1 overflow-y-auto pb-24">
        {activeView === 'login' && <LoginScreen />}
        {activeView === 'create' && <StoryCreator />}
        {activeView === 'discover' && <StoryArchive key="discover" />}
        {activeView === 'library' && <StoryArchive key="library" />}
        {activeView === 'profile' && <AccountScreen />}
        {activeView === 'admin' && <AdminDashboard />}
      </main>

      {/* persistent audio companion (z-60) */}
      <AudioCompanion />

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-surface/80 backdrop-blur-xl border-t border-slate-800 safe-area-bottom z-50">
        <div className="max-w-2xl mx-auto flex items-center justify-around py-1.5">
          {NAV_ITEMS.map(({ key, label, icon: Icon }) => {
            const isProfile = key === 'profile';
            const isGuest = isProfile && !user;
            const isActive = activeView === key;
            
            return (
              <button
                key={key}
                onClick={() => {
                  setActiveView(key);
                  if (useStore.getState().isReaderOpen) {
                    useStore.getState().setReaderOpen(false);
                  }
                }}
                className={`flex flex-col items-center gap-1 px-4 py-1.5 rounded-xl transition-all relative ${isActive
                  ? 'text-primary'
                  : 'text-slate-100 hover:text-white'
                  }`}
              >
                <div className={`transition-transform duration-300 ${key === 'create' ? '-rotate-[30deg]' : ''}`}>
                  <Icon className={`w-5 h-5 ${isActive ? 'stroke-[3]' : 'stroke-[2.5]'}`} />
                </div>
                <span className="text-[8px] font-mono uppercase tracking-[0.25em] font-medium">
                  {isGuest ? 'Anmelden' : label}
                </span>
                {isGuest && (
                  <div className="absolute top-1 right-2 w-2 h-2 rounded-full bg-amber-400 border-2 border-surface shadow-sm" />
                )}

              </button>
            );
          })}
        </div>
      </nav>

    </div>
  );
}

export default App;

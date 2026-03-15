import { useEffect } from 'react';
import { useStore } from './store/useStore';
import { PenTool, BookOpen, User, Feather, Compass } from 'lucide-react';
import { Toaster } from 'react-hot-toast';
import StoryCreator from './components/StoryCreator';
import StoryArchive from './components/StoryArchive';
import LoginScreen from './components/LoginScreen';
import AccountScreen from './components/AccountScreen';
import ReaderLayer from './components/ReaderLayer';
import AudioCompanion from './components/AudioCompanion';

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

      if (hash.startsWith('/story/')) {
        const storyId = hash.split('/')[2];
        if (storyId) {
          // Open reader for this story
          useStore.getState().setReaderOpen(true, storyId);
          return;
        }
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

      if (hash === '/create' || hash === '') {
        setActiveView('create');
        return;
      }
    };

    // Run once on load
    handleHashChange();

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, [setActiveView]);

  // Sync Store State -> URL Hash
  useEffect(() => {
    let desiredHash = '';
    const { isReaderOpen, readerStoryId } = useStore.getState();

    if (isReaderOpen && readerStoryId) {
      desiredHash = `#/story/${readerStoryId}`;
    } else if (activeView === 'library') {
      desiredHash = `#/library`;
    } else if (activeView === 'discover') {
      desiredHash = `#/discover`;
    } else if (activeView === 'create') {
      desiredHash = `#/create`;
    } else if (activeView === 'profile') {
      desiredHash = `#/profile`;
    } else if (activeView === 'login') {
      desiredHash = ``;
    }

    if (desiredHash !== '' && window.location.hash !== desiredHash) {
      window.history.pushState(null, '', desiredHash);
    }
  }, [activeView, useStore.getState().isReaderOpen, useStore.getState().readerStoryId]);

  if (isLoading && !isInitialized) {
    return (
      <div className="min-h-screen bg-[#F8F9FA] flex flex-col items-center justify-center w-full gap-8">
        <div className="relative">
          <div className="w-24 h-24 rounded-full border border-slate-100 flex items-center justify-center bg-white shadow-sm animate-pulse">
            <Feather className="w-10 h-10 text-[#2D5A4C]" />
          </div>
          <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-[#2D5A4C] rounded-full border-4 border-[#F8F9FA]" />
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
      {/* Reader Layer (z-40) */}
      <ReaderLayer />

      <Toaster position="top-center" />
      <main id="main-scroll-container" className="flex-1 overflow-y-auto pb-24">
        {activeView === 'login' && <LoginScreen />}
        {activeView === 'create' && <StoryCreator />}
        {activeView === 'discover' && <StoryArchive />}
        {activeView === 'library' && <StoryArchive />}
        {activeView === 'profile' && <AccountScreen />}
      </main>

      {/* persistent audio companion (z-60) */}
      <AudioCompanion />

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-surface/80 backdrop-blur-xl border-t border-slate-800 safe-area-bottom z-50">
        <div className="max-w-2xl mx-auto flex items-center justify-around py-2">
          {NAV_ITEMS.map(({ key, label, icon: Icon }) => {
            const isProfile = key === 'profile';
            const isGuest = isProfile && !user;
            
            return (
              <button
                key={key}
                onClick={() => setActiveView(key)}
                className={`flex flex-col items-center gap-1 px-4 py-2 rounded-xl transition-all relative ${activeView === key
                  ? 'text-primary'
                  : 'text-slate-500 hover:text-slate-300'
                  }`}
              >
                <Icon className={`w-5 h-5 ${activeView === key ? 'stroke-[2.5]' : 'stroke-[1.5]'}`} />
                <span className="text-[8px] font-mono uppercase tracking-[0.2em] font-medium">
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

      <Toaster position="top-center" />
    </div>
  );
}

export default App;

import { useEffect } from 'react';
import { useStore } from './store/useStore';
import { Loader2, PenTool, BookOpen, Headphones, Moon, User } from 'lucide-react';
import { Toaster } from 'react-hot-toast';
import StoryCreator from './components/StoryCreator';
import StoryArchive from './components/StoryArchive';
import StoryPlayer from './components/StoryPlayer';
import LoginScreen from './components/LoginScreen';
import AccountScreen from './components/AccountScreen';

const NAV_ITEMS = [
  { key: 'create' as const, label: 'Erstellen', icon: PenTool },
  { key: 'archive' as const, label: 'Archiv', icon: BookOpen },
  { key: 'player' as const, label: 'Player', icon: Headphones },
  { key: 'account' as const, label: 'Konto', icon: User },
];

function App() {
  const { fetchData, isLoading, error, isInitialized, activeView, setActiveView, selectedStoryId, setSelectedStoryId, user, token } = useStore();

  // Initial Data Fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auth Guard: Only redirect to login if we are in 'account' view and not logged in
  useEffect(() => {
    if (isInitialized && !user && !token && activeView === 'account') {
        setActiveView('login');
    }
  }, [isInitialized, user, token, activeView, setActiveView]);

  // Sync URL Hash -> Store State (Listeners for Back/Forward & direct link access)
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '');

      if (hash.startsWith('/player/')) {
        const storyId = hash.split('/')[2];
        if (storyId) {
          setActiveView('player');
          setSelectedStoryId(storyId);
          return;
        }
      }

      // If we are definitely not logged in, don't change other routes
      if (!localStorage.getItem('auth_token')) return;

      if (hash === '/archive') {
        setActiveView('archive');
        return;
      }

      if (hash === '/account') {
        setActiveView('account');
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
  }, [setActiveView, setSelectedStoryId]);

  // Sync Store State -> URL Hash (When clicking buttons in the UI)
  useEffect(() => {
    let desiredHash = '';
    if (activeView === 'player' && selectedStoryId) {
      desiredHash = `#/player/${selectedStoryId}`;
    } else if (activeView === 'archive') {
      desiredHash = `#/archive`;
    } else if (activeView === 'create') {
      desiredHash = `#/create`;
    } else if (activeView === 'account') {
      desiredHash = `#/account`;
    } else if (activeView === 'login') {
      desiredHash = ``; // Clear hash for login
    }

    if (desiredHash !== '' && window.location.hash !== desiredHash) {
      window.history.pushState(null, '', desiredHash);
    }
  }, [activeView, selectedStoryId]);

  if (isLoading && !isInitialized) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-indigo-50/30 flex flex-col items-center justify-center w-full gap-4">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/25 animate-pulse">
          <Moon className="w-8 h-8 text-white" />
        </div>
        <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
      </div>
    );
  }


  if (error && activeView !== 'login') {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-indigo-50/30 flex flex-col items-center justify-center w-full p-6 text-center">
        <div className="w-16 h-16 bg-red-100 text-red-500 rounded-2xl flex items-center justify-center mb-4 text-2xl">!</div>
        <h2 className="text-xl font-bold text-slate-800 mb-2">Verbindungsfehler</h2>
        <p className="text-slate-500 text-sm mb-6">{error}</p>
        <button onClick={() => fetchData()} className="px-6 py-3 bg-indigo-500 text-white font-medium rounded-xl hover:bg-indigo-600 transition-colors">
          Erneut versuchen
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-indigo-50/30 flex flex-col w-full">
      {/* Main Content */}
      <main id="main-scroll-container" className="flex-1 overflow-y-auto pb-24">
        {activeView === 'login' && <LoginScreen />}
        {activeView === 'create' && <StoryCreator />}
        {activeView === 'archive' && <StoryArchive />}
        {activeView === 'player' && <StoryPlayer />}
        {activeView === 'account' && <AccountScreen />}
      </main>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white/80 backdrop-blur-xl border-t border-slate-100 safe-area-bottom z-50">
        <div className="max-w-2xl mx-auto flex items-center justify-around py-2">
          {NAV_ITEMS.map(({ key, label, icon: Icon }) => {
            const isAccount = key === 'account';
            const isGuest = isAccount && !user;
            
            return (
              <button
                key={key}
                onClick={() => setActiveView(key)}
                className={`flex flex-col items-center gap-1 px-4 py-2 rounded-xl transition-all relative ${activeView === key
                  ? 'text-indigo-600'
                  : 'text-slate-400 hover:text-slate-600'
                  }`}
              >
                <Icon className={`w-5 h-5 ${activeView === key ? 'stroke-[2.5]' : ''}`} />
                <span className="text-[10px] font-semibold">
                  {isGuest ? 'Anmelden' : label}
                </span>
                {isGuest && (
                  <div className="absolute top-1 right-2 w-2 h-2 rounded-full bg-amber-400 border-2 border-white shadow-sm" />
                )}
                {activeView === key && !isGuest && (
                  <div className="w-1 h-1 rounded-full bg-indigo-500" />
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

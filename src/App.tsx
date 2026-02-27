import { useEffect } from 'react';
import { useStore } from './store/useStore';
import { Loader2, PenTool, BookOpen, Headphones, Moon } from 'lucide-react';
import { Toaster } from 'react-hot-toast';
import StoryCreator from './components/StoryCreator';
import StoryArchive from './components/StoryArchive';
import StoryPlayer from './components/StoryPlayer';

const NAV_ITEMS = [
  { key: 'create' as const, label: 'Erstellen', icon: PenTool },
  { key: 'archive' as const, label: 'Archiv', icon: BookOpen },
  { key: 'player' as const, label: 'Player', icon: Headphones },
];

function App() {
  const { fetchData, isLoading, error, isInitialized, activeView, setActiveView } = useStore();

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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

  if (error) {
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
      <main className="flex-1 overflow-y-auto pb-24">
        {activeView === 'create' && <StoryCreator />}
        {activeView === 'archive' && <StoryArchive />}
        {activeView === 'player' && <StoryPlayer />}
      </main>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white/80 backdrop-blur-xl border-t border-slate-100 safe-area-bottom z-50">
        <div className="max-w-2xl mx-auto flex items-center justify-around py-2">
          {NAV_ITEMS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveView(key)}
              className={`flex flex-col items-center gap-1 px-6 py-2 rounded-xl transition-all ${activeView === key
                ? 'text-indigo-600'
                : 'text-slate-400 hover:text-slate-600'
                }`}
            >
              <Icon className={`w-5 h-5 ${activeView === key ? 'stroke-[2.5]' : ''}`} />
              <span className="text-[10px] font-semibold">{label}</span>
              {activeView === key && (
                <div className="w-1 h-1 rounded-full bg-indigo-500" />
              )}
            </button>
          ))}
        </div>
      </nav>

      <Toaster position="top-center" />
    </div>
  );
}

export default App;

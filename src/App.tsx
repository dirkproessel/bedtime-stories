import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import { useStore } from './store/useStore';
import { Loader2 } from 'lucide-react';
import { Toaster } from 'react-hot-toast';

function Dashboard() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-4">Welcome to React + Supabase Starter</h1>
      <p className="text-slate-600 mb-6">
        This is your clean, generic template. It includes:
      </p>
      <ul className="list-disc pl-5 space-y-2 text-slate-700">
        <li><strong>Vite & React 19</strong> for fast development</li>
        <li><strong>Tailwind CSS v4</strong> for styling</li>
        <li><strong>Supabase</strong> pre-configured in <code>src/lib/supabase.ts</code></li>
        <li><strong>Zustand</strong> for state management</li>
        <li><strong>React Router</strong> for navigation</li>
        <li><strong>Coolify / Nixpacks</strong> config for SPA routing</li>
      </ul>
      <div className="mt-8 p-4 bg-primary/10 rounded-xl text-primary font-medium">
        Ready to build your next amazing app!
      </div>
    </div>
  );
}

function App() {
  const { fetchData, isLoading, error, isInitialized } = useStore();

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (isLoading && !isInitialized) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center w-full">
        <Loader2 className="w-10 h-10 text-primary animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center w-full p-6 text-center">
        <div className="w-16 h-16 bg-red-100 text-red-500 rounded-full flex items-center justify-center mb-4 text-2xl">!</div>
        <h2 className="text-xl font-bold text-slate-800 mb-2">Verbindungsfehler</h2>
        <p className="text-slate-500 text-sm">{error}</p>
        <button onClick={() => fetchData()} className="mt-6 btn-primary px-6 py-2">Erneut versuchen</button>
      </div>
    );
  }

  return (
    <BrowserRouter>
      {/* Full width container for responsive layout across devices */}
      <div className="min-h-screen bg-slate-50 flex flex-col w-full relative overflow-hidden">
        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto w-full bg-background">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <Toaster position="top-center" />
      </div>
    </BrowserRouter>
  );
}

export default App;

import { useState, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { getAudioUrl, fetchStory, getThumbUrl, type StoryDetail } from '../lib/api';
import { Play, Square, X, RotateCcw, RotateCw } from 'lucide-react';

const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
};

export default function AudioCompanion() {
    const { 
        showAudioCompanion, currentAudioStoryId, setAudioCompanion, 
        setReaderOpen 
    } = useStore();
    const [story, setStory] = useState<StoryDetail | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const audioRef = useRef<HTMLAudioElement>(null);

    useEffect(() => {
        if (showAudioCompanion && currentAudioStoryId) {
            fetchStory(currentAudioStoryId).then(s => {
                setStory(s);
                if (s.duration_seconds) setDuration(s.duration_seconds);
            });
        }
    }, [showAudioCompanion, currentAudioStoryId]);

    // Audio effects
    useEffect(() => {
        const audio = audioRef.current;
        if (!audio) return;

        const onTimeUpdate = () => setCurrentTime(audio.currentTime);
        const onLoaded = () => setDuration(audio.duration);
        const onEnded = () => setIsPlaying(false);
        const onPlay = () => setIsPlaying(true);
        const onPause = () => setIsPlaying(false);

        audio.addEventListener('timeupdate', onTimeUpdate);
        audio.addEventListener('loadedmetadata', onLoaded);
        audio.addEventListener('ended', onEnded);
        audio.addEventListener('play', onPlay);
        audio.addEventListener('pause', onPause);

        // Sync initial state if audio is already playing/loaded
        setIsPlaying(!audio.paused);
        if (audio.duration) setDuration(audio.duration);

        return () => {
            audio.removeEventListener('timeupdate', onTimeUpdate);
            audio.removeEventListener('loadedmetadata', onLoaded);
            audio.removeEventListener('ended', onEnded);
            audio.removeEventListener('play', onPlay);
            audio.removeEventListener('pause', onPause);
        };
    }, [showAudioCompanion]);

    // Source sync
    useEffect(() => {
        if (audioRef.current && currentAudioStoryId) {
            audioRef.current.src = getAudioUrl(currentAudioStoryId);
            audioRef.current.load();
            audioRef.current.play().catch(() => {});
        }
    }, [currentAudioStoryId]);

    if (!showAudioCompanion) return null;

    const progress = (currentTime / (duration || 1)) * 100 || 0;

    const skip = (seconds: number) => {
        if (audioRef.current) {
            audioRef.current.currentTime = Math.max(0, Math.min(audioRef.current.duration, audioRef.current.currentTime + seconds));
        }
    };

    const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
        if (audioRef.current && duration) {
            const rect = e.currentTarget.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const pct = x / rect.width;
            audioRef.current.currentTime = pct * duration;
        }
    };

    return (
        <div className="fixed bottom-0 left-0 right-0 lg:left-64 z-[150] px-4 pb-4 lg:pb-8 pointer-events-none">
            <audio ref={audioRef} />
            
            {story && (
                <div className="max-w-md mx-auto bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl p-2 pr-4 flex items-center gap-3 relative overflow-hidden group pointer-events-auto">
                    {/* Background Glow */}
                    <div className="absolute inset-0 bg-primary/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    
                    {/* Slim progress bar at the top - Clickable for seeking */}
                    <div 
                        className="absolute top-0 left-0 right-0 h-[6px] bg-slate-800 z-30 cursor-pointer group/progress"
                        onClick={handleSeek}
                    >
                        <div 
                            className="h-full bg-primary shadow-[0_0_8px_rgba(16,185,129,0.5)] transition-all duration-300 relative"
                            style={{ width: `${progress}%` }}
                        >
                            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-white opacity-0 group-hover/progress:opacity-100 transition-opacity" />
                        </div>
                    </div>

                    {/* Cover Image - Click to open Reader */}
                    <div 
                        onClick={() => setReaderOpen(true, story.id)}
                        className="w-12 h-12 rounded-2xl overflow-hidden shrink-0 cursor-pointer shadow-lg hover:scale-105 transition-transform border border-slate-700 relative z-20 mt-1"
                    >
                        <img src={getThumbUrl(story.id)} alt={story.title} className="w-full h-full object-cover grayscale-[10%] group-hover:grayscale-0 transition-all" />
                    </div>

                    {/* Title & info */}
                    <div className="flex-1 min-w-0 py-1 relative z-20 mt-1" onClick={() => setReaderOpen(true, story.id)}>
                        <h3 className="text-xs font-bold text-slate-100 truncate leading-tight group-hover:text-primary transition-colors">
                            {story.title}
                        </h3>
                        <p className="text-xs text-slate-500 uppercase tracking-widest truncate mt-0.5">
                            {formatTime(currentTime)} / {formatTime(duration)}
                        </p>
                    </div>

                    {/* Controls */}
                    <div className="flex items-center gap-1 relative z-20 mt-1">
                        <button 
                            onClick={(e) => { e.stopPropagation(); skip(-15); }}
                            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-primary hover:bg-primary/10 transition-all"
                            title="15s zurück"
                        >
                            <RotateCcw className="w-4 h-4" />
                        </button>

                        <button 
                            onClick={(e) => { e.stopPropagation(); audioRef.current?.paused ? audioRef.current.play() : audioRef.current?.pause(); }}
                            className="w-10 h-10 rounded-full flex items-center justify-center bg-primary/10 text-primary hover:bg-primary/20 hover:scale-110 active:scale-90 transition-all shadow-sm"
                        >
                            {isPlaying ? <Square className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-1" />}
                        </button>

                        <button 
                            onClick={(e) => { e.stopPropagation(); skip(15); }}
                            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-primary hover:bg-primary/10 transition-all"
                            title="15s vor"
                        >
                            <RotateCw className="w-4 h-4" />
                        </button>

                        <div className="w-px h-6 bg-slate-800 mx-1" />

                        <button 
                            onClick={(e) => { e.stopPropagation(); setAudioCompanion(false); }}
                            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-all"
                            aria-label="Schließen"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

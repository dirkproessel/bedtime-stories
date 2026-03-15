import { useState, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { getAudioUrl, fetchStory, getThumbUrl, type StoryDetail } from '../lib/api';
import { Play, Square, X } from 'lucide-react';

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

        return () => {
            audio.removeEventListener('timeupdate', onTimeUpdate);
            audio.removeEventListener('loadedmetadata', onLoaded);
            audio.removeEventListener('ended', onEnded);
            audio.removeEventListener('play', onPlay);
            audio.removeEventListener('pause', onPause);
        };
    }, []);

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

    return (
        <div className="fixed bottom-[84px] left-4 right-4 z-[60] animate-in slide-in-from-bottom duration-500">
            <audio ref={audioRef} />
            
            {story && (
                <div className="max-w-md mx-auto bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl p-2 pr-4 flex items-center gap-3 relative overflow-hidden group">
                    {/* Background Glow */}
                    <div className="absolute inset-0 bg-primary/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    
                    {/* Slim progress bar at the top */}
                    <div className="absolute top-0 left-0 right-0 h-[3px] bg-slate-800 z-10">
                        <div 
                            className="h-full bg-primary shadow-[0_0_8px_rgba(16,185,129,0.5)] transition-all duration-300"
                            style={{ width: `${progress}%` }}
                        />
                    </div>

                    {/* Cover Image - Click to open Reader */}
                    <div 
                        onClick={() => setReaderOpen(true, story.id)}
                        className="w-12 h-12 rounded-2xl overflow-hidden shrink-0 cursor-pointer shadow-lg hover:scale-105 transition-transform border border-slate-700 relative z-20"
                    >
                        <img src={getThumbUrl(story.id)} alt={story.title} className="w-full h-full object-cover grayscale-[10%] group-hover:grayscale-0 transition-all" />
                    </div>

                    {/* Title & info */}
                    <div className="flex-1 min-w-0 py-1 relative z-20" onClick={() => setReaderOpen(true, story.id)}>
                        <h3 className="text-[12px] font-serif font-bold text-slate-100 truncate leading-tight group-hover:text-primary transition-colors">
                            {story.title}
                        </h3>
                        <p className="text-[9px] font-mono text-slate-500 uppercase tracking-widest truncate mt-0.5">
                            {formatTime(currentTime)} / {formatTime(duration)}
                        </p>
                    </div>

                    {/* Controls */}
                    <div className="flex items-center gap-2 relative z-20">
                        <button 
                            onClick={(e) => { e.stopPropagation(); audioRef.current?.paused ? audioRef.current.play() : audioRef.current?.pause(); }}
                            className="w-10 h-10 rounded-full flex items-center justify-center bg-primary/10 text-primary hover:bg-primary/20 hover:scale-110 active:scale-90 transition-all shadow-sm"
                        >
                            {isPlaying ? <Square className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current ml-1" />}
                        </button>
                        <button 
                            onClick={(e) => { e.stopPropagation(); setAudioCompanion(false); }}
                            className="w-9 h-9 rounded-full flex items-center justify-center text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-all"
                            aria-label="Schließen"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

import { useState, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { getAudioUrl, fetchStory, getThumbUrl, type StoryDetail } from '../lib/api';
import { Play, Pause, X } from 'lucide-react';
import { voiceName } from '../lib/voices';

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
                <div className="max-w-md mx-auto bg-white/80 backdrop-blur-xl border border-slate-100 rounded-3xl shadow-2xl p-2 pr-4 flex items-center gap-3 relative overflow-hidden group">
                    {/* Slim progress bar at the top */}
                    <div className="absolute top-0 left-0 right-0 h-[2px] bg-slate-100">
                        <div 
                            className="h-full bg-[#2D5A4C] transition-all duration-300"
                            style={{ width: `${progress}%` }}
                        />
                    </div>

                    {/* Cover Image - Click to open Reader */}
                    <div 
                        onClick={() => setReaderOpen(true, story.id)}
                        className="w-12 h-12 rounded-2xl overflow-hidden shrink-0 cursor-pointer shadow-sm hover:scale-105 transition-transform"
                    >
                        <img src={getThumbUrl(story.id)} alt={story.title} className="w-full h-full object-cover" />
                    </div>

                    {/* Title & info */}
                    <div className="flex-1 min-w-0" onClick={() => setReaderOpen(true, story.id)}>
                        <h3 className="text-[11px] font-serif font-bold text-slate-900 truncate">{story.title}</h3>
                        <p className="text-[9px] font-mono text-slate-400 uppercase tracking-widest truncate">
                            {voiceName(story.voice_key)} • Vorlesen
                        </p>
                    </div>

                    {/* Controls */}
                    <div className="flex items-center gap-1">
                        <button 
                            onClick={() => audioRef.current?.paused ? audioRef.current.play() : audioRef.current?.pause()}
                            className="w-10 h-10 rounded-full flex items-center justify-center text-[#2D5A4C] hover:bg-[#F0FDF4] transition-colors"
                        >
                            {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current ml-1" />}
                        </button>
                        <button 
                            onClick={() => setAudioCompanion(false)}
                            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-300 hover:text-slate-500 transition-colors"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

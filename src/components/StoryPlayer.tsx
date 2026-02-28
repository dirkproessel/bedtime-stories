import { useState, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { getAudioUrl, fetchStory, getRssFeedUrl, type StoryDetail } from '../lib/api';
import {
    Play, Pause, SkipBack, SkipForward,
    ChevronDown, ChevronUp, Rss, Copy, ArrowLeft, Moon
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function StoryPlayer() {
    const { selectedStoryId, setActiveView } = useStore();
    const [story, setStory] = useState<StoryDetail | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [showChapters, setShowChapters] = useState(false);
    const [showRss, setShowRss] = useState(false);

    // Create the audio element once outside of React's render cycle.
    // This is the KEY fix: the ref is always valid, and React can never re-create
    // or re-load the element when state changes (which caused seeks to reset).
    const audioRef = useRef<HTMLAudioElement>(new Audio());

    // Attach event listeners once on mount
    useEffect(() => {
        const audio = audioRef.current;

        const onTimeUpdate = () => setCurrentTime(audio.currentTime);
        const onLoaded = () => { if (audio.duration && isFinite(audio.duration)) setDuration(audio.duration); };
        const onEnded = () => setIsPlaying(false);
        const onPlay = () => setIsPlaying(true);
        const onPause = () => setIsPlaying(false);

        audio.addEventListener('timeupdate', onTimeUpdate);
        audio.addEventListener('loadedmetadata', onLoaded);
        audio.addEventListener('durationchange', onLoaded);
        audio.addEventListener('canplay', onLoaded);
        audio.addEventListener('ended', onEnded);
        audio.addEventListener('play', onPlay);
        audio.addEventListener('pause', onPause);

        return () => {
            audio.pause();
            audio.removeEventListener('timeupdate', onTimeUpdate);
            audio.removeEventListener('loadedmetadata', onLoaded);
            audio.removeEventListener('durationchange', onLoaded);
            audio.removeEventListener('canplay', onLoaded);
            audio.removeEventListener('ended', onEnded);
            audio.removeEventListener('play', onPlay);
            audio.removeEventListener('pause', onPause);
        };
    }, []);

    // Load audio when the selected story changes
    useEffect(() => {
        const audio = audioRef.current;
        setCurrentTime(0);
        setDuration(0);
        setIsPlaying(false);
        if (selectedStoryId) {
            audio.src = getAudioUrl(selectedStoryId);
            audio.load();
        } else {
            audio.src = '';
        }
    }, [selectedStoryId]);

    // Fetch story metadata
    useEffect(() => {
        setStory(null);
        if (selectedStoryId) {
            fetchStory(selectedStoryId)
                .then(setStory)
                .catch(() => toast.error('Geschichte konnte nicht geladen werden'));
        }
    }, [selectedStoryId]);

    const togglePlay = () => {
        const audio = audioRef.current;
        if (isPlaying) { audio.pause(); } else { audio.play(); }
    };

    const skip = (seconds: number) => {
        const audio = audioRef.current;
        audio.currentTime = Math.max(0, Math.min(audio.currentTime + seconds, duration));
    };

    const seek = (e: React.ChangeEvent<HTMLInputElement>) => {
        const time = parseFloat(e.target.value);
        audioRef.current.currentTime = time;
        setCurrentTime(time);
    };

    const formatTime = (s: number) => {
        if (!s || !isFinite(s)) return '0:00';
        const m = Math.floor(s / 60);
        const sec = Math.floor(s % 60);
        return `${m}:${sec.toString().padStart(2, '0')}`;
    };

    const copyRssUrl = () => {
        navigator.clipboard.writeText(getRssFeedUrl());
        toast.success('RSS-Feed URL kopiert!');
    };

    if (!selectedStoryId) {
        return (
            <div className="p-6 flex flex-col items-center justify-center min-h-[60vh]">
                <Moon className="w-12 h-12 text-slate-200 mb-4" />
                <p className="text-slate-400 text-sm">Wähle eine Geschichte aus dem Archiv</p>
            </div>
        );
    }

    if (!story) {
        return (
            <div className="p-6 flex flex-col items-center justify-center min-h-[60vh]">
                <div className="w-16 h-16 rounded-full border-4 border-indigo-200 border-t-indigo-500 animate-spin mb-4" />
                <p className="text-slate-400 text-sm">Lade Geschichte…</p>
            </div>
        );
    }

    return (
        <div className="p-4 sm:p-6 max-w-2xl mx-auto">
            {/* Back button */}
            <button
                onClick={() => setActiveView('archive')}
                className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-600 transition-colors mb-6"
            >
                <ArrowLeft className="w-4 h-4" />
                Zurück zum Archiv
            </button>

            {/* Cover / Title */}
            <div className="text-center mb-8">
                {story.image_url ? (
                    <div className="w-48 h-48 mx-auto rounded-3xl overflow-hidden mb-6 shadow-xl border-4 border-white">
                        <img src={story.image_url} alt={story.title} className="w-full h-full object-cover" />
                    </div>
                ) : (
                    <div className="w-32 h-32 mx-auto rounded-3xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center mb-6 shadow-xl shadow-purple-500/25">
                        <Moon className="w-16 h-16 text-white/90" />
                    </div>
                )}
                <h1 className="text-xl font-bold text-slate-900">{story.title}</h1>
                <p className="text-sm text-slate-400 mt-1">{story.chapter_count} Kapitel · {formatTime(story.duration_seconds || 0)}</p>
            </div>

            {/* Progress */}
            <div className="mb-4">
                <input
                    type="range"
                    min={0}
                    max={duration || 0}
                    value={currentTime}
                    onChange={seek}
                    className="w-full h-1.5 rounded-full bg-slate-200 accent-indigo-500 cursor-pointer appearance-none [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-indigo-500 [&::-webkit-slider-thumb]:shadow-md"
                />
                <div className="flex justify-between text-xs text-slate-400 mt-1">
                    <span>{formatTime(currentTime)}</span>
                    <span>{formatTime(duration)}</span>
                </div>
            </div>

            {/* Controls */}
            <div className="flex items-center justify-center gap-6 mb-8">
                <button onClick={() => skip(-30)} className="w-12 h-12 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 flex items-center justify-center transition-all">
                    <SkipBack className="w-5 h-5" />
                </button>
                <button
                    onClick={togglePlay}
                    className="w-16 h-16 rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-600 text-white flex items-center justify-center shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 transition-all active:scale-95"
                >
                    {isPlaying ? <Pause className="w-7 h-7" /> : <Play className="w-7 h-7 ml-1" />}
                </button>
                <button onClick={() => skip(30)} className="w-12 h-12 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 flex items-center justify-center transition-all">
                    <SkipForward className="w-5 h-5" />
                </button>
            </div>

            {/* Chapters Toggle */}
            {story.chapters && story.chapters.length > 0 && (
                <div className="mb-4">
                    <button
                        onClick={() => setShowChapters(!showChapters)}
                        className="w-full flex items-center justify-between p-4 bg-white border-2 border-slate-100 rounded-2xl hover:border-slate-200 transition-all"
                    >
                        <span className="text-sm font-semibold text-slate-700">📖 Kapitel & Text</span>
                        {showChapters ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                    </button>
                    {showChapters && (
                        <div className="mt-2 space-y-3">
                            {story.chapters.map((ch, i) => (
                                <div key={i} className="p-4 bg-white border-2 border-slate-100 rounded-2xl">
                                    <h3 className="text-sm font-bold text-slate-700 mb-2">Kapitel {i + 1}: {ch.title}</h3>
                                    <p className="text-xs text-slate-500 leading-relaxed whitespace-pre-line">{ch.text}</p>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* RSS Feed */}
            <div className="mb-4">
                <button
                    onClick={() => setShowRss(!showRss)}
                    className="w-full flex items-center justify-between p-4 bg-white border-2 border-slate-100 rounded-2xl hover:border-slate-200 transition-all"
                >
                    <span className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                        <Rss className="w-4 h-4 text-orange-500" />
                        Podcast-Feed
                    </span>
                    {showRss ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </button>
                {showRss && (
                    <div className="mt-2 p-4 bg-white border-2 border-slate-100 rounded-2xl">
                        <p className="text-xs text-slate-500 mb-3">Füge diese URL in deine Podcast-App ein:</p>
                        <div className="flex items-center gap-2">
                            <code className="flex-1 text-xs bg-slate-50 text-slate-600 p-2.5 rounded-lg truncate">
                                {getRssFeedUrl()}
                            </code>
                            <button
                                onClick={copyRssUrl}
                                className="shrink-0 w-10 h-10 rounded-xl bg-slate-50 text-slate-400 flex items-center justify-center hover:bg-indigo-50 hover:text-indigo-500 transition-colors"
                            >
                                <Copy className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

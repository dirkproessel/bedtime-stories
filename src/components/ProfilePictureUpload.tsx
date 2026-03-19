import React, { useState, useRef, useEffect } from 'react';
import { Upload, X, Check, Loader2, ZoomIn, ZoomOut } from 'lucide-react';

interface ProfilePictureUploadProps {
    onUpload: (blob: Blob) => Promise<void>;
    onClose: () => void;
}

export default function ProfilePictureUpload({ onUpload, onClose }: ProfilePictureUploadProps) {
    const [imageSrc, setImageSrc] = useState<string | null>(null);
    const [imageObj, setImageObj] = useState<HTMLImageElement | null>(null);
    const [scale, setScale] = useState(1);
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState(false);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const MASK_SIZE = 256;

    useEffect(() => {
        if (imageSrc) {
            const img = new Image();
            img.src = imageSrc;
            img.onload = () => {
                setImageObj(img);
                // initial scale to cover the mask completely
                const initialScale = Math.max(MASK_SIZE / img.width, MASK_SIZE / img.height);
                setScale(initialScale);
                setPosition({ x: 0, y: 0 });
            };
        }
    }, [imageSrc]);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const file = e.target.files[0];
            const reader = new FileReader();
            reader.onload = (e) => {
                if (e.target?.result) {
                    setImageSrc(e.target.result as string);
                }
            };
            reader.readAsDataURL(file);
        }
    };

    const handleMouseDown = (e: React.MouseEvent | React.TouchEvent) => {
        e.preventDefault();
        setIsDragging(true);
        const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
        const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;
        setDragStart({ x: clientX - position.x, y: clientY - position.y });
    };

    const handleMouseMove = (e: React.MouseEvent | React.TouchEvent) => {
        if (!isDragging) return;
        const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
        const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;
        
        let newX = clientX - dragStart.x;
        let newY = clientY - dragStart.y;

        if (imageObj) {
            // Constrain movement so the image always covers the mask
            const scaledWidth = imageObj.width * scale;
            const scaledHeight = imageObj.height * scale;
            const minX = MASK_SIZE / 2 - scaledWidth / 2;
            const maxX = scaledWidth / 2 - MASK_SIZE / 2;
            const minY = MASK_SIZE / 2 - scaledHeight / 2;
            const maxY = scaledHeight / 2 - MASK_SIZE / 2;

            newX = Math.max(minX, Math.min(newX, maxX));
            newY = Math.max(minY, Math.min(newY, maxY));
        }

        setPosition({ x: newX, y: newY });
    };

    const handleMouseUp = () => {
        setIsDragging(false);
    };

    const handleZoom = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newScale = parseFloat(e.target.value);
        if (imageObj) {
            // Ensure new scale still covers the mask, adjust position if needed
            const scaledWidth = imageObj.width * newScale;
            const scaledHeight = imageObj.height * newScale;
            const minX = MASK_SIZE / 2 - scaledWidth / 2;
            const maxX = scaledWidth / 2 - MASK_SIZE / 2;
            const minY = MASK_SIZE / 2 - scaledHeight / 2;
            const maxY = scaledHeight / 2 - MASK_SIZE / 2;

            let newX = position.x;
            let newY = position.y;

            if (scaledWidth < MASK_SIZE || scaledHeight < MASK_SIZE) {
                // Cannot zoom out more than what covers the mask
                return;
            }

            newX = Math.max(minX, Math.min(newX, maxX));
            newY = Math.max(minY, Math.min(newY, maxY));
            
            setPosition({ x: newX, y: newY });
        }
        setScale(newScale);
    };

    const handleSave = async () => {
        if (!imageObj) return;
        setIsUploading(true);

        const canvas = document.createElement('canvas');
        canvas.width = 512;
        canvas.height = 512;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Ratio between final rendered image (512x512) and the visual mask (256x256)
        const exportRatio = 512 / MASK_SIZE;

        // Fill background just in case
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, 512, 512);

        // Center point of the canvas
        const cx = 512 / 2;
        const cy = 512 / 2;

        // Draw image onto canvas properly shifted and scaled
        ctx.translate(cx, cy);
        ctx.scale(scale * exportRatio, scale * exportRatio);
        
        ctx.drawImage(
            imageObj,
            -imageObj.width / 2 + (position.x / scale),
            -imageObj.height / 2 + (position.y / scale)
        );

        canvas.toBlob(async (blob) => {
            if (blob) {
                try {
                    await onUpload(blob);
                } finally {
                    setIsUploading(false);
                }
            } else {
                setIsUploading(false);
            }
        }, 'image/jpeg', 0.9);
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
            <div className="bg-surface border border-white/10 rounded-3xl p-6 w-full max-w-md shadow-2xl relative">
                
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-xl font-bold text-white">Profilbild ändern</h3>
                    <button onClick={onClose} className="p-2 bg-white/5 hover:bg-white/10 rounded-full transition-colors text-slate-300">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {!imageSrc ? (
                    <div className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-white/20 rounded-2xl bg-white/5 space-y-4">
                        <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center">
                            <Upload className="w-8 h-8 text-emerald-400" />
                        </div>
                        <p className="text-slate-300 text-sm text-center font-medium">
                            Ziehe ein Bild hierher oder klicke, um eines auszuwählen.
                        </p>
                        <button 
                            onClick={() => fileInputRef.current?.click()}
                            className="btn-primary"
                        >
                            Bild auswählen
                        </button>
                        <input 
                            ref={fileInputRef}
                            type="file" 
                            accept="image/*" 
                            onChange={handleFileSelect}
                            className="hidden" 
                        />
                    </div>
                ) : (
                    <div className="space-y-6">
                        {/* Editor View */}
                        <div className="relative w-full aspect-square bg-black/50 rounded-2xl overflow-hidden flex items-center justify-center touch-none">
                            <div 
                                className="w-full h-full relative cursor-move overflow-hidden mask-container"
                                onMouseDown={handleMouseDown}
                                onMouseMove={handleMouseMove}
                                onMouseUp={handleMouseUp}
                                onMouseLeave={handleMouseUp}
                                onTouchStart={handleMouseDown}
                                onTouchMove={handleMouseMove}
                                onTouchEnd={handleMouseUp}
                            >
                                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[256px] h-[256px] rounded-full ring-4 ring-emerald-500 shadow-[0_0_0_9999px_rgba(0,0,0,0.6)] z-10 pointer-events-none" />
                                {imageObj && (
                                    <img 
                                        src={imageSrc} 
                                        alt="Profil Preview" 
                                        className="absolute top-1/2 left-1/2"
                                        style={{
                                            transform: `translate(calc(-50% + ${position.x}px), calc(-50% + ${position.y}px)) scale(${scale})`,
                                            maxWidth: 'none',
                                            transformOrigin: 'center'
                                        }}
                                        draggable={false}
                                    />
                                )}
                            </div>
                        </div>

                        {/* Controls */}
                        {imageObj && (
                            <div className="space-y-4">
                                <div className="flex items-center gap-4 text-slate-400">
                                    <ZoomOut className="w-5 h-5" />
                                    <input 
                                        type="range" 
                                        min={Math.max(MASK_SIZE / imageObj.width, MASK_SIZE / imageObj.height)} 
                                        max={3} 
                                        step="0.01" 
                                        value={scale} 
                                        onChange={handleZoom}
                                        className="flex-1 accent-emerald-500 bg-white/10 h-2 rounded-full outline-none"
                                    />
                                    <ZoomIn className="w-5 h-5" />
                                </div>
                                <p className="text-xs text-slate-500 text-center uppercase tracking-wider">
                                    Bewege das Bild um den Fokus zu setzen
                                </p>
                            </div>
                        )}

                        <div className="flex gap-3">
                            <button 
                                onClick={() => setImageSrc(null)}
                                className="flex-1 py-3 bg-white/5 hover:bg-white/10 text-white font-medium rounded-xl transition-colors"
                            >
                                Zurücksetzen
                            </button>
                            <button 
                                onClick={handleSave}
                                disabled={isUploading}
                                className="flex-1 py-3 bg-emerald-500 hover:bg-emerald-400 text-white font-medium rounded-xl transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                            >
                                {isUploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Check className="w-5 h-5" />}
                                Speichern
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

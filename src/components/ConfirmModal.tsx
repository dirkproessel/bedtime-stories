import { X, AlertCircle } from 'lucide-react';

interface ConfirmModalProps {
    isOpen: boolean;
    title: string;
    message: string;
    confirmLabel?: string;
    cancelLabel?: string;
    onConfirm: () => void;
    onClose: () => void;
    isDanger?: boolean;
}

export default function ConfirmModal({
    isOpen,
    title,
    message,
    confirmLabel = 'Löschen',
    cancelLabel = 'Abbrechen',
    onConfirm,
    onClose,
    isDanger = true
}: ConfirmModalProps) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-background/80 backdrop-blur-md animate-in fade-in duration-300">
            <div 
                className="fixed inset-0" 
                onClick={onClose}
            />
            <div className="relative w-full max-w-sm bg-surface/90 backdrop-blur-2xl rounded-[2.5rem] shadow-2xl border border-slate-800/50 overflow-hidden animate-in zoom-in duration-300">
                <div className="p-8">
                    <button
                        onClick={onClose}
                        className="absolute top-6 right-6 p-2 text-slate-500 hover:text-slate-300 rounded-full hover:bg-slate-800 transition-all"
                    >
                        <X className="w-5 h-5" />
                    </button>

                    <div className="flex flex-col items-center text-center">
                        <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-6 shadow-lg ${
                            isDanger 
                                ? 'bg-red-500/20 text-red-500 shadow-red-500/10' 
                                : 'bg-primary/20 text-primary shadow-primary/10'
                        }`}>
                            <AlertCircle className="w-8 h-8" />
                        </div>

                        <h2 className="text-xl font-bold text-text mb-3">
                            {title}
                        </h2>
                        
                        <p className="text-slate-400 text-sm leading-relaxed mb-8">
                            {message}
                        </p>

                        <div className="flex flex-col gap-3 w-full">
                            <button
                                onClick={() => {
                                    onConfirm();
                                    onClose();
                                }}
                                className={`w-full py-4 rounded-2xl font-bold transition-all active:scale-[0.98] ${
                                    isDanger
                                        ? 'bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/20'
                                        : 'btn-primary'
                                }`}
                            >
                                {confirmLabel}
                            </button>
                            
                            <button
                                onClick={onClose}
                                className="w-full py-3 text-sm font-bold text-slate-500 hover:text-slate-300 transition-colors"
                            >
                                {cancelLabel}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Utility to smartly merge Tailwind utility classes
 */
export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export interface StoreState {
    isInitialized: boolean;
    isLoading: boolean;
    error: string | null;
    fetchData: () => Promise<void>;
}

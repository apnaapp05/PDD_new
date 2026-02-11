// Helper to get user-specific chat key
// Place this in lib/chatStorage.ts or inline in components

export const getChatStorageKey = (prefix: string = 'chat_history'): string => {
    if (typeof window === 'undefined') return prefix;

    const token = localStorage.getItem('token');
    if (!token) return prefix; // Fallback to old key if not logged in

    try {
        // Decode JWT to get user ID (without verification - just for ID extraction)
        const payload = JSON.parse(atob(token.split('.')[1]));
        const userId = payload.sub || payload.user_id || payload.id;
        return `${prefix}_${userId}`;
    } catch (e) {
        console.error('Failed to decode token for chat storage:', e);
        return prefix; // Fallback
    }
};

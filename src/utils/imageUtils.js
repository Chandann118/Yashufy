/**
 * Utility for handling thumbnail URLs with multiple robust fallbacks.
 */
export const getThumbnailUrl = (song) => {
    if (!song) return 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=500';

    const videoId = song.videoId || song.id;

    // 1. Array of potential thumbnail sources in order of preference
    const fallbacks = [
        song.thumbnail,
        song.artwork,
        // Build YouTube official thumbnail URLs if it's a YT track
        videoId && videoId.length === 11 ? `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg` : null,
        videoId && videoId.length === 11 ? `https://img.youtube.com/vi/${videoId}/hqdefault.jpg` : null,
        videoId && videoId.length === 11 ? `https://img.youtube.com/vi/${videoId}/mqdefault.jpg` : null,
        // Global high-quality fallback
        'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=500'
    ];

    // Return the first valid non-null URL
    return fallbacks.find(url => url && typeof url === 'string' && url.trim() !== '') || 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=500';
};

import { store } from '../store';

/**
 * Service to manage backend warming for Render free tier.
 */
class WarmupManager {
    constructor() {
        this.warmedIds = new Set();
        this.lastWarmup = 0;
    }

    /**
     * Proactively warm up a list of tracks.
     * @param {Array} tracks - List of tracks to warm up.
     */
    async warmUpTracks(tracks) {
        if (!tracks || tracks.length === 0) return;

        const state = store.getState();
        const backendUrl = state.settings.backendUrl;
        if (!backendUrl) return;

        // Only warm up every 5 minutes to avoid spamming
        const now = Date.now();
        if (now - this.lastWarmup < 5 * 60 * 1000) return;

        const idsToWarm = tracks
            .map(t => t.videoId || t.id)
            .filter(id => id && !this.warmedIds.has(id))
            .slice(0, 10);

        if (idsToWarm.length === 0) return;

        try {
            console.log(`Warming up ${idsToWarm.length} tracks...`);
            const idsParam = idsToWarm.join(',');
            await fetch(`${backendUrl}/warmup?ids=${idsParam}`, {
                headers: { 'Bypass-Tunnel-Reminder': 'true' }
            });

            idsToWarm.forEach(id => this.warmedIds.add(id));
            this.lastWarmup = now;
        } catch (error) {
            console.log('Warmup failed:', error.message);
        }
    }

    /**
     * Reset warmed IDs (e.g. on cache clear).
     */
    reset() {
        this.warmedIds.clear();
        this.lastWarmup = 0;
    }
}

export const warmupManager = new WarmupManager();

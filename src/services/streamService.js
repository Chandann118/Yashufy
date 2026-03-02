import { store } from '../store';

/**
 * Service to handle stream URL fetching with retry logic and 202 status handling.............
 */
export const fetchStreamWithRetry = async (item, retryAttempt = 0) => {
    const maxRetries = 5;
    const state = store.getState();
    const backendUrl = state.settings.backendUrl;

    if (!backendUrl) throw new Error('Backend URL not configured');

    const videoId = item.videoId || item.id;
    const url = `${backendUrl}/stream-info?id=${videoId}&title=${encodeURIComponent(item.title)}&artist=${encodeURIComponent(item.artist)}&duration_total=${item.duration || ''}`;

    try {
        const response = await fetch(url, {
            headers: { 'Bypass-Tunnel-Reminder': 'true' }
        });
        n
        // Handle 202 Accepted (Processing/Waking Up)
        if (response.status === 202) {
            console.log(`Backend is processing (202). Retrying in attempt ${retryAttempt + 1}...`);
            if (retryAttempt < maxRetries) {
                const waitTime = Math.pow(2, retryAttempt) * 1000;
                await new Promise(resolve => setTimeout(resolve, waitTime));
                return fetchStreamWithRetry(item, retryAttempt + 1);
            }
            throw new Error('Backend processing timeout (202)');
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Server responded with ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.log(`Stream fetch error (Attempt ${retryAttempt + 1}):`, error.message);

        // Handle network errors or server downtime (Cold Start)
        if (retryAttempt < maxRetries) {
            const waitTime = Math.pow(2, retryAttempt) * 1000;
            console.log(`Backend might be waking up. Retrying in ${waitTime}ms...`);
            await new Promise(resolve => setTimeout(resolve, waitTime));
            return fetchStreamWithRetry(item, retryAttempt + 1);
        }

        throw error;
    }
};

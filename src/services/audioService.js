import { Audio } from 'expo-av';

let playbackInstance = null;
let currentTrackData = null;

export const setupPlayer = async () => {
    try {
        await Audio.setAudioModeAsync({
            allowsRecordingIOS: false,
            staysActiveInBackground: true,
            interruptionModeIOS: 1, // InterruptionModeIOS.DoNotMix
            playsInSilentModeIOS: true,
            shouldDuckAndroid: true,
            interruptionModeAndroid: 1, // InterruptionModeAndroid.DoNotMix
            playThroughEarpieceAndroid: false,
        });
    } catch (error) {
        console.log('Error setting up audio mode:', error);
    }
};

export const playTrack = async (track, onPlaybackStatusUpdate, retryAttempt = 0) => {
    const maxRetries = 3;
    try {
        if (playbackInstance !== null) {
            await playbackInstance.unloadAsync();
            playbackInstance = null;
        }

        const { sound } = await Audio.Sound.createAsync(
            {
                uri: track.url,
                headers: { 'User-Agent': 'VortexMusic/1.0' }
            },
            { shouldPlay: true },
            onPlaybackStatusUpdate
        );

        playbackInstance = sound;
        currentTrackData = track;

        return sound;
    } catch (error) {
        console.log(`Error playing track (Attempt ${retryAttempt + 1}):`, error);

        if (retryAttempt < maxRetries) {
            const waitTime = Math.pow(2, retryAttempt) * 1000;
            console.log(`Retrying in ${waitTime}ms...`);
            await new Promise(resolve => setTimeout(resolve, waitTime));
            return playTrack(track, onPlaybackStatusUpdate, retryAttempt + 1);
        }

        throw error;
    }
};

export const togglePlayback = async (isPlaying) => {
    if (playbackInstance) {
        if (isPlaying) {
            await playbackInstance.playAsync();
        } else {
            await playbackInstance.pauseAsync();
        }
    }
};

export const seekTo = async (positionMillis) => {
    if (playbackInstance) {
        await playbackInstance.setPositionAsync(positionMillis);
    }
};

export const getPlaybackInstance = () => playbackInstance;

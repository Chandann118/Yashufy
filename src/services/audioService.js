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

export const playTrack = async (track, onPlaybackStatusUpdate) => {
    try {
        if (playbackInstance !== null) {
            await playbackInstance.unloadAsync();
            playbackInstance = null;
        }

        const { sound } = await Audio.Sound.createAsync(
            { uri: track.url },
            { shouldPlay: true },
            onPlaybackStatusUpdate
        );

        playbackInstance = sound;
        currentTrackData = track;

        return sound;
    } catch (error) {
        console.log('Error playing track:', error);
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

export const getPlaybackInstance = () => playbackInstance;

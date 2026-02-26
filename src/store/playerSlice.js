import { createSlice } from '@reduxjs/toolkit';

const initialState = {
    currentTrack: null,
    isPlaying: false,
    queue: [],
    playbackState: 'idle',
    volume: 1.0,
    repeatMode: 'off', // off, all, one
    isShuffle: false,
    currentIndex: -1,
};

const playerSlice = createSlice({
    name: 'player',
    initialState,
    reducers: {
        setTrack: (state, action) => {
            state.currentTrack = action.payload;
        },
        setPlaying: (state, action) => {
            state.isPlaying = action.payload;
        },
        setQueue: (state, action) => {
            state.queue = action.payload;
        },
        setPlaybackState: (state, action) => {
            state.playbackState = action.payload;
        },
        setVolume: (state, action) => {
            state.volume = action.payload;
        },
        toggleShuffle: (state) => {
            state.isShuffle = !state.isShuffle;
        },
        toggleRepeatMode: (state) => {
            const modes = ['off', 'all', 'one'];
            const currentIndex = modes.indexOf(state.repeatMode);
            state.repeatMode = modes[(currentIndex + 1) % modes.length];
        },
        setCurrentIndex: (state, action) => {
            state.currentIndex = action.payload;
        }
    },
});

export const {
    setTrack, setPlaying, setQueue, setPlaybackState,
    setVolume, toggleShuffle, toggleRepeatMode, setCurrentIndex
} = playerSlice.actions;

export default playerSlice.reducer;

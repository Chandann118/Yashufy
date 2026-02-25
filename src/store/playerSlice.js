import { createSlice } from '@reduxjs/toolkit';

const initialState = {
    currentTrack: null,
    isPlaying: false,
    queue: [],
    playbackState: 'idle',
    volume: 1.0,
    repeatMode: 'off', // off, one, all
    isShuffle: false,
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
        setRepeatMode: (state, action) => {
            state.repeatMode = action.payload;
        },
    },
});

export const {
    setTrack, setPlaying, setQueue, setPlaybackState,
    setVolume, toggleShuffle, setRepeatMode
} = playerSlice.actions;

export default playerSlice.reducer;

import { createSlice } from '@reduxjs/toolkit';

const initialState = {
    playlists: [],
    likedSongs: [],
    offlineDownloads: [],
    folders: [],
};

const librarySlice = createSlice({
    name: 'library',
    initialState,
    reducers: {
        addPlaylist: (state, action) => {
            state.playlists.push(action.payload);
        },
        toggleLikeSong: (state, action) => {
            const song = action.payload;
            const index = state.likedSongs.findIndex(s => s.id === song.id);
            if (index >= 0) {
                state.likedSongs.splice(index, 1);
            } else {
                state.likedSongs.push(song);
            }
        },
        addOfflineDownload: (state, action) => {
            state.offlineDownloads.push(action.payload);
        },
    },
});

export const { addPlaylist, toggleLikeSong, addOfflineDownload } = librarySlice.actions;
export default librarySlice.reducer;

import { createSlice } from '@reduxjs/toolkit';

const initialState = {
    backendUrl: 'https://yashufy.onrender.com', // Your live Render URL
    discoveryUrl: '',
};

const settingsSlice = createSlice({
    name: 'settings',
    initialState,
    reducers: {
        setBackendUrl: (state, action) => {
            state.backendUrl = action.payload;
        },
        setDiscoveryUrl: (state, action) => {
            state.discoveryUrl = action.payload;
        },
    },
});

export const { setBackendUrl, setDiscoveryUrl } = settingsSlice.actions;
export default settingsSlice.reducer;

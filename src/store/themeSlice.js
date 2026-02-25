import { createSlice } from '@reduxjs/toolkit';

const initialState = {
    mode: 'dark', // light, dark
    accent: '#FF9933', // Saffron
};

const themeSlice = createSlice({
    name: 'theme',
    initialState,
    reducers: {
        setThemeMode: (state, action) => {
            state.mode = action.payload;
        },
        setAccent: (state, action) => {
            state.accent = action.payload;
        },
    },
});

export const { setThemeMode, setAccent } = themeSlice.actions;
export default themeSlice.reducer;

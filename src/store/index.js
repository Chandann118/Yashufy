import { configureStore } from '@reduxjs/toolkit';
import playerReducer from './playerSlice';
import libraryReducer from './librarySlice';
import themeReducer from './themeSlice';
import settingsReducer from './settingsSlice';

export const store = configureStore({
    reducer: {
        player: playerReducer,
        library: libraryReducer,
        theme: themeReducer,
        settings: settingsReducer,
    },
    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware({
            serializableCheck: false,
        }),
});

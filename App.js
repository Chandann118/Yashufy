import "./global.css";
import React, { useEffect } from 'react';
import { Provider } from 'react-redux';
import { NavigationContainer } from '@react-navigation/native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { store } from './src/store';
import RootNavigator from './src/navigation';
import { setupPlayer } from './src/services/audioService';
import { setBackendUrl } from './src/store/settingsSlice';

export default function App() {
  useEffect(() => {
    setupPlayer();
    syncBackendWithDiscovery();
  }, []);

  const syncBackendWithDiscovery = async () => {
    const state = store.getState();
    const discoveryUrl = state.settings.discoveryUrl;

    if (discoveryUrl && discoveryUrl.startsWith('http')) {
      try {
        console.log('Syncing backend URL from:', discoveryUrl);
        const response = await fetch(discoveryUrl);
        const text = await response.text();
        const latestUrl = text.trim();

        if (latestUrl.startsWith('http')) {
          console.log('Updating backend URL to:', latestUrl);
          store.dispatch(setBackendUrl(latestUrl));
        }
      } catch (error) {
        console.error('Failed to sync backend URL:', error);
      }
    }
  };

  return (
    <Provider store={store}>
      <SafeAreaProvider>
        <NavigationContainer>
          <RootNavigator />
        </NavigationContainer>
      </SafeAreaProvider>
    </Provider>
  );
}

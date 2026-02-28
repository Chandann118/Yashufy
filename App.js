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

    // Keep-alive ping every 10 minutes to prevent Render sleep
    const keepAlive = setInterval(async () => {
      try {
        const state = store.getState();
        const backendUrl = state.settings.backendUrl;
        if (backendUrl) {
          console.log('Sending keep-alive ping...');
          await fetch(`${backendUrl}/health`, { headers: { 'Bypass-Tunnel-Reminder': 'true' } });
        }
      } catch (e) {
        console.log('Keep-alive ping failed:', e.message);
      }
    }, 10 * 60 * 1000);

    return () => clearInterval(keepAlive);
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

import React, { useEffect } from 'react';
import { StatusBar, Platform } from 'react-native';
import { Provider } from 'react-redux';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { store, useAppDispatch } from './store/store';
import { checkAuth } from './store/authSlice';
import { recordingManager } from './services/recording';
import RootNavigator from './navigation/RootNavigator';

function AppContent() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    // Check if user has a stored auth token
    dispatch(checkAuth());

    // Initialize the recording upload queue
    recordingManager.initialize();
  }, [dispatch]);

  return (
    <>
      <StatusBar barStyle="light-content" backgroundColor="#0F172A" />
      <RootNavigator />
    </>
  );
}

export default function App() {
  return (
    <Provider store={store}>
      <SafeAreaProvider>
        <AppContent />
      </SafeAreaProvider>
    </Provider>
  );
}

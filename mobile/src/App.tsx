import React, { useEffect, Component, ErrorInfo, ReactNode } from 'react';
import { StatusBar, View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Provider } from 'react-redux';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { store, useAppDispatch } from './store/store';
import { checkAuth } from './store/authSlice';
import RootNavigator from './navigation/RootNavigator';

// SBA Colors
const SBA_DARK = '#0A1628';
const SBA_GOLD = '#D4A843';
const SBA_WHITE = '#F8FAFC';
const SBA_MUTED = '#94A3B8';

// ── Error Boundary ──────────────────────────────────────────────────

interface ErrorBoundaryState {
  hasError: boolean;
  errorMessage: string;
}

class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, errorMessage: '' };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, errorMessage: error.message || 'Unknown error' };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('App Error Boundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <View style={errorStyles.container}>
          <Text style={errorStyles.icon}>!</Text>
          <Text style={errorStyles.title}>Something went wrong</Text>
          <Text style={errorStyles.message}>{this.state.errorMessage}</Text>
          <TouchableOpacity
            style={errorStyles.button}
            onPress={() => this.setState({ hasError: false, errorMessage: '' })}
          >
            <Text style={errorStyles.buttonText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      );
    }
    return this.props.children;
  }
}

const errorStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: SBA_DARK,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  icon: {
    fontSize: 48,
    fontWeight: '700',
    color: SBA_GOLD,
    marginBottom: 16,
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
    color: SBA_WHITE,
    marginBottom: 8,
  },
  message: {
    fontSize: 14,
    color: SBA_MUTED,
    textAlign: 'center',
    marginBottom: 24,
  },
  button: {
    backgroundColor: SBA_GOLD,
    borderRadius: 10,
    paddingHorizontal: 32,
    paddingVertical: 14,
  },
  buttonText: {
    color: SBA_DARK,
    fontSize: 16,
    fontWeight: '600',
  },
});

// ── App Content ─────────────────────────────────────────────────────

function AppContent() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    // Check stored auth token - wrapped in try/catch for safety
    try {
      dispatch(checkAuth());
    } catch (e) {
      console.error('checkAuth dispatch failed:', e);
    }

    // Initialize recording manager lazily (don't block app startup)
    setTimeout(() => {
      try {
        const { recordingManager } = require('./services/recording');
        recordingManager.initialize().catch((e: any) => {
          console.error('Recording manager init failed:', e);
        });
      } catch (e) {
        console.error('Recording manager import failed:', e);
      }
    }, 2000);
  }, [dispatch]);

  return (
    <>
      <StatusBar barStyle="light-content" backgroundColor={SBA_DARK} />
      <RootNavigator />
    </>
  );
}

// ── Root App ────────────────────────────────────────────────────────

export default function App() {
  return (
    <ErrorBoundary>
      <Provider store={store}>
        <SafeAreaProvider>
          <AppContent />
        </SafeAreaProvider>
      </Provider>
    </ErrorBoundary>
  );
}

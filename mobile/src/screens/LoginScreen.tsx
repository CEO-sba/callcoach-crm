import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { useAppDispatch, useAppSelector } from '../store/store';
import { login, clearError } from '../store/authSlice';

// SBA Brand Colors
const SBA_NAVY = '#1E3A8A';
const SBA_DARK = '#0A1628';
const SBA_DARK_CARD = '#111D33';
const SBA_GOLD = '#D4A843';
const SBA_GOLD_LIGHT = '#E8C97A';
const SBA_WHITE = '#F8FAFC';
const SBA_MUTED = '#94A3B8';
const SBA_BORDER = '#1E3553';
const SBA_ERROR = '#EF4444';

export default function LoginScreen() {
  const dispatch = useAppDispatch();
  const { isLoginLoading, error } = useAppSelector((state) => state.auth);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = () => {
    if (!email.trim() || !password.trim()) return;
    dispatch(login({ email: email.trim(), password }));
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.inner}>
          {/* Brand Header */}
          <View style={styles.brandSection}>
            <View style={styles.logoContainer}>
              <View style={styles.logoIcon}>
                <Text style={styles.logoIconText}>CC</Text>
              </View>
            </View>
            <Text style={styles.appName}>CallCoach</Text>
            <View style={styles.divider} />
            <Text style={styles.brandName}>Skin Business Accelerator</Text>
            <Text style={styles.tagline}>
              AI-Powered Call Analysis for Clinics
            </Text>
          </View>

          {/* Login Form */}
          <View style={styles.formCard}>
            <Text style={styles.formTitle}>Sign In</Text>

            <View style={styles.inputWrapper}>
              <Text style={styles.inputLabel}>Email</Text>
              <TextInput
                style={styles.input}
                placeholder="Enter your email"
                placeholderTextColor="#4A5568"
                value={email}
                onChangeText={(t) => {
                  setEmail(t);
                  if (error) dispatch(clearError());
                }}
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
              />
            </View>

            <View style={styles.inputWrapper}>
              <Text style={styles.inputLabel}>Password</Text>
              <TextInput
                style={styles.input}
                placeholder="Enter your password"
                placeholderTextColor="#4A5568"
                value={password}
                onChangeText={(t) => {
                  setPassword(t);
                  if (error) dispatch(clearError());
                }}
                secureTextEntry
              />
            </View>

            {error ? (
              <Text style={styles.error}>
                {typeof error === 'string' ? error : 'Something went wrong. Please try again.'}
              </Text>
            ) : null}

            <TouchableOpacity
              style={[styles.button, isLoginLoading && styles.buttonDisabled]}
              onPress={handleLogin}
              disabled={isLoginLoading}
              activeOpacity={0.8}
            >
              {isLoginLoading ? (
                <ActivityIndicator color={SBA_DARK} />
              ) : (
                <Text style={styles.buttonText}>Sign In</Text>
              )}
            </TouchableOpacity>
          </View>

          {/* Footer */}
          <Text style={styles.footer}>
            Powered by SBA Growth Systems
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: SBA_DARK,
  },
  scrollContent: {
    flexGrow: 1,
  },
  inner: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 28,
    paddingVertical: 40,
  },

  // Brand Section
  brandSection: {
    alignItems: 'center',
    marginBottom: 36,
  },
  logoContainer: {
    marginBottom: 16,
  },
  logoIcon: {
    width: 72,
    height: 72,
    borderRadius: 20,
    backgroundColor: SBA_NAVY,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: SBA_GOLD,
  },
  logoIconText: {
    fontSize: 28,
    fontWeight: '800',
    color: SBA_GOLD,
    letterSpacing: 1,
  },
  appName: {
    fontSize: 32,
    fontWeight: '700',
    color: SBA_WHITE,
    letterSpacing: 1,
  },
  divider: {
    width: 40,
    height: 2,
    backgroundColor: SBA_GOLD,
    marginVertical: 12,
    borderRadius: 1,
  },
  brandName: {
    fontSize: 13,
    fontWeight: '600',
    color: SBA_GOLD,
    letterSpacing: 1.5,
    textTransform: 'uppercase',
  },
  tagline: {
    fontSize: 13,
    color: SBA_MUTED,
    marginTop: 8,
  },

  // Form Card
  formCard: {
    backgroundColor: SBA_DARK_CARD,
    borderRadius: 16,
    padding: 24,
    borderWidth: 1,
    borderColor: SBA_BORDER,
  },
  formTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: SBA_WHITE,
    marginBottom: 20,
  },
  inputWrapper: {
    marginBottom: 16,
  },
  inputLabel: {
    fontSize: 13,
    fontWeight: '500',
    color: SBA_MUTED,
    marginBottom: 6,
  },
  input: {
    backgroundColor: SBA_DARK,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 15,
    color: SBA_WHITE,
    borderWidth: 1,
    borderColor: SBA_BORDER,
  },
  error: {
    color: SBA_ERROR,
    fontSize: 13,
    textAlign: 'center',
    marginBottom: 8,
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    padding: 10,
    borderRadius: 8,
  },
  button: {
    backgroundColor: SBA_GOLD,
    borderRadius: 10,
    paddingVertical: 15,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: SBA_DARK,
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: 0.5,
  },

  // Footer
  footer: {
    fontSize: 12,
    color: '#475569',
    textAlign: 'center',
    marginTop: 28,
  },
});

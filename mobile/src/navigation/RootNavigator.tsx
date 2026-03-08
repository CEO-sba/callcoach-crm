import React, { useEffect } from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useAppSelector, useAppDispatch } from '../store/store';
import { finishInitializing } from '../store/authSlice';

import LoginScreen from '../screens/LoginScreen';
import ContactsScreen from '../screens/ContactsScreen';
import DialerScreen from '../screens/DialerScreen';
import ActiveCallScreen from '../screens/ActiveCallScreen';
import CallHistoryScreen from '../screens/CallHistoryScreen';
import CallDetailScreen from '../screens/CallDetailScreen';
import SettingsScreen from '../screens/SettingsScreen';

// SBA Brand Colors
const SBA_NAVY = '#1E3A8A';
const SBA_DARK = '#0A1628';
const SBA_GOLD = '#D4A843';
const SBA_WHITE = '#F8FAFC';
const SBA_MUTED = '#64748B';
const SBA_BORDER = '#1E293B';

// ── Type Definitions ────────────────────────────────────────────────

export type RootStackParamList = {
  Auth: undefined;
  Main: undefined;
  ActiveCall: {
    phoneNumber: string;
    callerName: string;
  };
  CallDetail: {
    callId: string;
    callerName?: string;
  };
};

export type AuthStackParamList = {
  Login: undefined;
};

export type MainTabParamList = {
  Contacts: undefined;
  Dialer: { phoneNumber?: string; callerName?: string } | undefined;
  History: undefined;
  Settings: undefined;
};

// ── Navigators ──────────────────────────────────────────────────────

const RootStack = createNativeStackNavigator<RootStackParamList>();
const AuthStack = createNativeStackNavigator<AuthStackParamList>();
const MainTab = createBottomTabNavigator<MainTabParamList>();

// ── Splash Screen ──────────────────────────────────────────────────

function SplashScreen() {
  const dispatch = useAppDispatch();

  // Safety timeout: if auth check hangs, force show login after 3 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      dispatch(finishInitializing());
    }, 3000);
    return () => clearTimeout(timer);
  }, [dispatch]);

  return (
    <View style={splashStyles.container}>
      <View style={splashStyles.logoBox}>
        <Text style={splashStyles.logoText}>CC</Text>
      </View>
      <Text style={splashStyles.logo}>CallCoach</Text>
      <Text style={splashStyles.subtitle}>by Skin Business Accelerator</Text>
      <ActivityIndicator
        size="large"
        color={SBA_GOLD}
        style={splashStyles.spinner}
      />
    </View>
  );
}

const splashStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: SBA_DARK,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoBox: {
    width: 80,
    height: 80,
    borderRadius: 20,
    backgroundColor: SBA_NAVY,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: SBA_GOLD,
    marginBottom: 20,
  },
  logoText: {
    fontSize: 32,
    fontWeight: '800',
    color: SBA_GOLD,
    letterSpacing: 1,
  },
  logo: {
    fontSize: 36,
    fontWeight: '700',
    color: SBA_WHITE,
    letterSpacing: 1,
  },
  subtitle: {
    fontSize: 14,
    color: SBA_GOLD,
    marginTop: 8,
    letterSpacing: 0.5,
  },
  spinner: {
    marginTop: 32,
  },
});

// ── Auth Navigator ──────────────────────────────────────────────────

function AuthNavigator() {
  return (
    <AuthStack.Navigator screenOptions={{ headerShown: false }}>
      <AuthStack.Screen name="Login" component={LoginScreen} />
    </AuthStack.Navigator>
  );
}

// ── Main Tab Navigator ──────────────────────────────────────────────

function MainTabNavigator() {
  return (
    <MainTab.Navigator
      screenOptions={({ route }) => ({
        headerStyle: { backgroundColor: SBA_DARK },
        headerTintColor: SBA_WHITE,
        tabBarStyle: {
          backgroundColor: SBA_DARK,
          borderTopColor: SBA_BORDER,
          paddingBottom: 4,
          height: 60,
        },
        tabBarActiveTintColor: SBA_GOLD,
        tabBarInactiveTintColor: SBA_MUTED,
        tabBarIcon: ({ color, size }) => {
          let iconName = 'phone';
          if (route.name === 'Contacts') iconName = 'contacts';
          else if (route.name === 'Dialer') iconName = 'dialpad';
          else if (route.name === 'History') iconName = 'history';
          else if (route.name === 'Settings') iconName = 'settings';
          return <Icon name={iconName} size={size} color={color} />;
        },
      })}
    >
      <MainTab.Screen
        name="Contacts"
        component={ContactsScreen}
        options={{ title: 'Contacts' }}
      />
      <MainTab.Screen
        name="Dialer"
        component={DialerScreen}
        options={{ title: 'Dialer' }}
      />
      <MainTab.Screen
        name="History"
        component={CallHistoryScreen}
        options={{ title: 'Call History' }}
      />
      <MainTab.Screen
        name="Settings"
        component={SettingsScreen}
        options={{ title: 'Settings' }}
      />
    </MainTab.Navigator>
  );
}

// ── Root Navigator ──────────────────────────────────────────────────

export default function RootNavigator() {
  const { isLoggedIn, isInitializing } = useAppSelector((state) => state.auth);

  if (isInitializing) {
    return <SplashScreen />;
  }

  return (
    <NavigationContainer>
      <RootStack.Navigator screenOptions={{ headerShown: false }}>
        {!isLoggedIn ? (
          <RootStack.Screen name="Auth" component={AuthNavigator} />
        ) : (
          <>
            <RootStack.Screen name="Main" component={MainTabNavigator} />
            <RootStack.Screen
              name="ActiveCall"
              component={ActiveCallScreen}
              options={{
                presentation: 'fullScreenModal',
                animation: 'slide_from_bottom',
              }}
            />
            <RootStack.Screen
              name="CallDetail"
              component={CallDetailScreen}
              options={{
                headerShown: true,
                headerStyle: { backgroundColor: SBA_DARK },
                headerTintColor: SBA_WHITE,
                title: 'Call Analysis',
              }}
            />
          </>
        )}
      </RootStack.Navigator>
    </NavigationContainer>
  );
}

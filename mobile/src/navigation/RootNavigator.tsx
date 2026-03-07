import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useAppSelector } from '../store/store';

import LoginScreen from '../screens/LoginScreen';
import ContactsScreen from '../screens/ContactsScreen';
import DialerScreen from '../screens/DialerScreen';
import ActiveCallScreen from '../screens/ActiveCallScreen';
import CallHistoryScreen from '../screens/CallHistoryScreen';
import CallDetailScreen from '../screens/CallDetailScreen';
import SettingsScreen from '../screens/SettingsScreen';

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
        headerStyle: { backgroundColor: '#0F172A' },
        headerTintColor: '#F8FAFC',
        tabBarStyle: {
          backgroundColor: '#0F172A',
          borderTopColor: '#1E293B',
          paddingBottom: 4,
          height: 60,
        },
        tabBarActiveTintColor: '#3B82F6',
        tabBarInactiveTintColor: '#64748B',
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
  const { isLoggedIn, isLoading } = useAppSelector((state) => state.auth);

  if (isLoading) {
    return null; // Splash screen would go here
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
                headerStyle: { backgroundColor: '#0F172A' },
                headerTintColor: '#F8FAFC',
                title: 'Call Analysis',
              }}
            />
          </>
        )}
      </RootStack.Navigator>
    </NavigationContainer>
  );
}

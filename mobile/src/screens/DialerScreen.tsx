import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Platform,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { dialer, requestCallPermissions } from '../services/nativeModules';
import { useAppSelector } from '../store/store';
import DialPad from '../components/DialPad';
import { RootStackParamList, MainTabParamList } from '../navigation/RootNavigator';

type DialerRouteProp = RouteProp<MainTabParamList, 'Dialer'>;
type RootNavProp = NativeStackNavigationProp<RootStackParamList>;

export default function DialerScreen() {
  const navigation = useNavigation<RootNavProp>();
  const route = useRoute<DialerRouteProp>();
  const [phoneNumber, setPhoneNumber] = useState('');
  const [callerName, setCallerName] = useState('');
  const { contacts } = useAppSelector((state) => state.contacts);

  // Pre-fill from navigation params (when tapping a contact)
  useEffect(() => {
    if (route.params?.phoneNumber) {
      setPhoneNumber(route.params.phoneNumber);
      setCallerName(route.params.callerName || '');
    }
  }, [route.params]);

  // Look up contact name when number changes
  useEffect(() => {
    if (phoneNumber && !callerName) {
      const match = contacts.find((c) =>
        c.phone.replace(/[^\d]/g, '') === phoneNumber.replace(/[^\d]/g, '')
      );
      if (match) setCallerName(match.name);
    }
  }, [phoneNumber, contacts, callerName]);

  const handleDigit = (digit: string) => {
    setPhoneNumber((prev) => prev + digit);
  };

  const handleDelete = () => {
    setPhoneNumber((prev) => prev.slice(0, -1));
  };

  const handleCall = async () => {
    if (!phoneNumber.trim()) {
      Alert.alert('Enter a number', 'Please enter a phone number to call.');
      return;
    }

    if (Platform.OS === 'android') {
      const granted = await requestCallPermissions();
      if (!granted) {
        Alert.alert(
          'Permissions Required',
          'CallCoach needs phone and recording permissions to make and record calls.'
        );
        return;
      }
    }

    try {
      // Navigate to active call screen
      navigation.navigate('ActiveCall', {
        phoneNumber: phoneNumber.trim(),
        callerName: callerName || phoneNumber.trim(),
      });

      // Initiate the call
      await dialer.makeCall(phoneNumber.trim());
    } catch (error: any) {
      Alert.alert('Call Failed', error.message || 'Could not initiate call.');
    }
  };

  return (
    <View style={styles.container}>
      {/* Number Display */}
      <View style={styles.display}>
        {callerName ? (
          <Text style={styles.callerName}>{callerName}</Text>
        ) : null}
        <Text
          style={styles.phoneNumber}
          numberOfLines={1}
          adjustsFontSizeToFit
        >
          {phoneNumber || 'Enter number'}
        </Text>
      </View>

      {/* Dial Pad */}
      <DialPad onPress={handleDigit} onDelete={handleDelete} />

      {/* Call Button */}
      <View style={styles.callRow}>
        <TouchableOpacity
          style={[styles.callButton, !phoneNumber && styles.callButtonDisabled]}
          onPress={handleCall}
          disabled={!phoneNumber}
        >
          <Icon name="call" size={32} color="#FFF" />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
    justifyContent: 'space-between',
    paddingVertical: 16,
  },
  display: {
    alignItems: 'center',
    paddingHorizontal: 32,
    paddingVertical: 24,
  },
  callerName: {
    color: '#94A3B8',
    fontSize: 16,
    marginBottom: 4,
  },
  phoneNumber: {
    color: '#F8FAFC',
    fontSize: 32,
    fontWeight: '400',
    fontVariant: ['tabular-nums'],
    minHeight: 40,
  },
  callRow: {
    alignItems: 'center',
    paddingBottom: 16,
  },
  callButton: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: '#22C55E',
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 4,
    shadowColor: '#22C55E',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  callButtonDisabled: {
    backgroundColor: '#334155',
    shadowOpacity: 0,
  },
});

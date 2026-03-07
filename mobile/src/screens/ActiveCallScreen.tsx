import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Platform,
  Animated,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { recorder, callEvents, CallStateEvent } from '../services/nativeModules';
import { recordingManager } from '../services/recording';
import { useAppDispatch, useAppSelector } from '../store/store';
import {
  setActiveCall,
  updateActiveCall,
  addUploadItem,
} from '../store/recordingSlice';
import CallTimer from '../components/CallTimer';
import { RootStackParamList } from '../navigation/RootNavigator';

type ScreenRouteProp = RouteProp<RootStackParamList, 'ActiveCall'>;
type NavProp = NativeStackNavigationProp<RootStackParamList>;

export default function ActiveCallScreen() {
  const navigation = useNavigation<NavProp>();
  const route = useRoute<ScreenRouteProp>();
  const dispatch = useAppDispatch();
  const { autoRecord } = useAppSelector((state) => state.recording);

  const { phoneNumber, callerName } = route.params;
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingPath, setRecordingPath] = useState<string | null>(null);
  const [callStartTime] = useState(Date.now());
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeaker, setIsSpeaker] = useState(false);

  // Recording indicator pulse
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (isRecording) {
      const pulse = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 0.3,
            duration: 800,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 800,
            useNativeDriver: true,
          }),
        ])
      );
      pulse.start();
      return () => pulse.stop();
    }
  }, [isRecording, pulseAnim]);

  // Set active call in Redux
  useEffect(() => {
    dispatch(
      setActiveCall({
        phoneNumber,
        callerName,
        startTime: callStartTime,
        recordingPath: null,
        isRecording: false,
        isConnected: false,
      })
    );

    return () => {
      dispatch(setActiveCall(null));
    };
  }, [dispatch, phoneNumber, callerName, callStartTime]);

  // Listen for call state changes (Android)
  useEffect(() => {
    if (!callEvents) {
      // iOS or no call events available: assume connected immediately
      setIsConnected(true);
      if (autoRecord) startRecording();
      return;
    }

    const subscription = callEvents.addListener(
      'onCallStateChanged',
      async (event: CallStateEvent) => {
        if (event.state === 'callConnected') {
          setIsConnected(true);
          dispatch(updateActiveCall({ isConnected: true }));
          if (autoRecord) {
            await startRecording();
          }
        } else if (event.state === 'callEnded') {
          await handleCallEnded();
        }
      }
    );

    return () => subscription.remove();
  }, [autoRecord]);

  const startRecording = async () => {
    if (Platform.OS !== 'android') return;
    const path = await recorder.startRecording(phoneNumber);
    if (path) {
      setRecordingPath(path);
      setIsRecording(true);
      dispatch(updateActiveCall({ recordingPath: path, isRecording: true }));
    }
  };

  const stopRecording = async () => {
    const path = await recorder.stopRecording();
    setIsRecording(false);
    dispatch(updateActiveCall({ isRecording: false }));
    return path || recordingPath;
  };

  const handleCallEnded = async () => {
    let finalPath = recordingPath;
    if (isRecording) {
      finalPath = await stopRecording();
    }

    // Queue for upload if we have a recording
    if (finalPath) {
      const durationSeconds = Math.round((Date.now() - callStartTime) / 1000);
      const rec = await recordingManager.addRecording({
        filePath: finalPath,
        callerName,
        callerPhone: phoneNumber,
        callType: 'sales',
        direction: 'outbound',
        durationSeconds,
      });

      dispatch(
        addUploadItem({
          id: rec.id,
          callerName,
          callerPhone: phoneNumber,
          status: 'pending',
          progress: 0,
        })
      );
    }

    navigation.goBack();
  };

  const handleEndCall = async () => {
    await handleCallEnded();
  };

  const toggleRecording = async () => {
    if (isRecording) {
      await stopRecording();
    } else {
      await startRecording();
    }
  };

  return (
    <View style={styles.container}>
      {/* Caller Info */}
      <View style={styles.callerSection}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {callerName.charAt(0).toUpperCase()}
          </Text>
        </View>
        <Text style={styles.callerName}>{callerName}</Text>
        <Text style={styles.callerPhone}>{phoneNumber}</Text>

        {isConnected ? (
          <CallTimer startTime={callStartTime} />
        ) : (
          <Text style={styles.statusText}>Calling...</Text>
        )}

        {/* Recording Indicator */}
        {isRecording && (
          <View style={styles.recordingIndicator}>
            <Animated.View
              style={[styles.recordingDot, { opacity: pulseAnim }]}
            />
            <Text style={styles.recordingText}>Recording</Text>
          </View>
        )}
      </View>

      {/* Action Buttons */}
      <View style={styles.actions}>
        <View style={styles.actionRow}>
          <TouchableOpacity
            style={[styles.actionButton, isMuted && styles.actionActive]}
            onPress={() => setIsMuted(!isMuted)}
          >
            <Icon
              name={isMuted ? 'mic-off' : 'mic'}
              size={28}
              color={isMuted ? '#3B82F6' : '#F8FAFC'}
            />
            <Text style={styles.actionLabel}>
              {isMuted ? 'Unmute' : 'Mute'}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.actionButton, isSpeaker && styles.actionActive]}
            onPress={() => setIsSpeaker(!isSpeaker)}
          >
            <Icon
              name={isSpeaker ? 'volume-up' : 'volume-down'}
              size={28}
              color={isSpeaker ? '#3B82F6' : '#F8FAFC'}
            />
            <Text style={styles.actionLabel}>Speaker</Text>
          </TouchableOpacity>

          {Platform.OS === 'android' && (
            <TouchableOpacity
              style={[styles.actionButton, isRecording && styles.actionRecording]}
              onPress={toggleRecording}
            >
              <Icon
                name={isRecording ? 'stop' : 'fiber-manual-record'}
                size={28}
                color={isRecording ? '#EF4444' : '#F8FAFC'}
              />
              <Text style={styles.actionLabel}>
                {isRecording ? 'Stop Rec' : 'Record'}
              </Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* End Call */}
      <View style={styles.endCallRow}>
        <TouchableOpacity style={styles.endCallButton} onPress={handleEndCall}>
          <Icon name="call-end" size={36} color="#FFF" />
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
    paddingTop: 80,
    paddingBottom: 60,
  },
  callerSection: {
    alignItems: 'center',
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#3B82F6',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  avatarText: { color: '#FFF', fontSize: 32, fontWeight: '600' },
  callerName: { color: '#F8FAFC', fontSize: 24, fontWeight: '600' },
  callerPhone: { color: '#94A3B8', fontSize: 16, marginTop: 4, marginBottom: 24 },
  statusText: { color: '#94A3B8', fontSize: 20, fontWeight: '300' },
  recordingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 16,
    backgroundColor: '#7F1D1D40',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  recordingDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#EF4444',
    marginRight: 8,
  },
  recordingText: { color: '#EF4444', fontSize: 14, fontWeight: '600' },
  actions: {
    paddingHorizontal: 32,
  },
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 32,
  },
  actionButton: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: '#1E293B',
    justifyContent: 'center',
    alignItems: 'center',
  },
  actionActive: {
    backgroundColor: '#1E3A5F',
  },
  actionRecording: {
    backgroundColor: '#7F1D1D40',
  },
  actionLabel: {
    color: '#94A3B8',
    fontSize: 11,
    marginTop: 4,
  },
  endCallRow: {
    alignItems: 'center',
  },
  endCallButton: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: '#EF4444',
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 4,
    shadowColor: '#EF4444',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
});

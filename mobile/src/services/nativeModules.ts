/**
 * CallCoach CRM - Native Module Bridge
 *
 * Platform-aware wrappers for Android native dialer and call recorder.
 * On iOS, falls back to cloud telephony or manual upload.
 */
import {
  NativeModules,
  NativeEventEmitter,
  Platform,
  PermissionsAndroid,
  Linking,
} from 'react-native';

const { DialerModule, CallRecorderModule } = NativeModules;

// ── Types ──────────────────────────────────────────────────────────

export interface RecordingResult {
  filePath: string;
  status: 'recording' | 'stopped';
}

export interface CallStateEvent {
  state: 'callRinging' | 'callConnected' | 'callEnded';
  number: string | null;
}

// ── Permission Helpers ─────────────────────────────────────────────

export async function requestCallPermissions(): Promise<boolean> {
  if (Platform.OS !== 'android') return true;

  try {
    const results = await PermissionsAndroid.requestMultiple([
      PermissionsAndroid.PERMISSIONS.CALL_PHONE,
      PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
      PermissionsAndroid.PERMISSIONS.READ_PHONE_STATE,
    ]);

    return Object.values(results).every(
      (s) => s === PermissionsAndroid.RESULTS.GRANTED
    );
  } catch {
    return false;
  }
}

// ── Dialer ─────────────────────────────────────────────────────────

export const dialer = {
  /**
   * Initiate a phone call using the device's SIM card.
   * Android: Uses native Intent.ACTION_CALL
   * iOS: Opens the Phone app (no native recording possible)
   */
  async makeCall(phoneNumber: string): Promise<void> {
    const cleaned = phoneNumber.replace(/[^\d+]/g, '');

    if (Platform.OS === 'android' && DialerModule) {
      const granted = await requestCallPermissions();
      if (!granted) throw new Error('Call permissions denied');
      await DialerModule.makeCall(cleaned);
    } else {
      // iOS fallback: open phone app
      const url = `tel:${cleaned}`;
      const canOpen = await Linking.canOpenURL(url);
      if (canOpen) {
        await Linking.openURL(url);
      } else {
        throw new Error('Cannot open phone dialer');
      }
    }
  },
};

// ── Call Recorder ──────────────────────────────────────────────────

export const recorder = {
  /**
   * Start recording the active call.
   * Only works on Android with VOICE_CALL audio source.
   * Returns the file path where the recording is being saved.
   */
  async startRecording(phoneNumber: string): Promise<string | null> {
    if (Platform.OS !== 'android' || !CallRecorderModule) {
      console.log('Call recording not available on this platform');
      return null;
    }

    try {
      const granted = await PermissionsAndroid.request(
        PermissionsAndroid.PERMISSIONS.RECORD_AUDIO
      );
      if (granted !== PermissionsAndroid.RESULTS.GRANTED) {
        throw new Error('RECORD_AUDIO permission denied');
      }

      const result: RecordingResult = await CallRecorderModule.startRecording(phoneNumber);
      return result.filePath;
    } catch (error: any) {
      // VOICE_CALL source may not be available on all devices
      console.error('Recording start failed:', error.message);

      // Try MIC source as fallback (records only user's side)
      try {
        const result: RecordingResult = await CallRecorderModule.startRecordingMic(phoneNumber);
        return result.filePath;
      } catch {
        return null;
      }
    }
  },

  /**
   * Stop the active recording and return the file path.
   */
  async stopRecording(): Promise<string | null> {
    if (Platform.OS !== 'android' || !CallRecorderModule) return null;

    try {
      const result: RecordingResult = await CallRecorderModule.stopRecording();
      return result.filePath;
    } catch (error: any) {
      console.error('Recording stop failed:', error.message);
      return null;
    }
  },

  /**
   * Check if a recording is currently active.
   */
  async isRecording(): Promise<boolean> {
    if (Platform.OS !== 'android' || !CallRecorderModule) return false;
    try {
      return await CallRecorderModule.isRecording();
    } catch {
      return false;
    }
  },
};

// ── Call State Events ──────────────────────────────────────────────

/**
 * Event emitter for call state changes (Android only).
 * Emits 'onCallStateChanged' with CallStateEvent payload.
 *
 * Usage:
 *   const sub = callEvents.addListener('onCallStateChanged', (event) => {
 *     if (event.state === 'callConnected') startRecording();
 *     if (event.state === 'callEnded') stopRecording();
 *   });
 *   return () => sub.remove();
 */
export const callEvents =
  Platform.OS === 'android' && NativeModules.CallStateModule
    ? new NativeEventEmitter(NativeModules.CallStateModule)
    : null;

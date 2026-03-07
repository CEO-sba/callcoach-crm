package com.callcoachmobile;

import android.Manifest;
import android.content.pm.PackageManager;
import android.media.MediaRecorder;
import android.os.Build;
import android.os.Environment;

import androidx.core.app.ActivityCompat;

import com.facebook.react.bridge.Promise;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;
import com.facebook.react.bridge.WritableMap;
import com.facebook.react.bridge.Arguments;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * Native module for recording phone calls on Android.
 *
 * Uses MediaRecorder with AudioSource.VOICE_CALL to capture both sides of the call.
 * Falls back to AudioSource.MIC if VOICE_CALL is not available (records user side only).
 *
 * Output: AAC encoded .m4a files (optimal for speech transcription).
 * Files saved to: Documents/CallCoachRecordings/
 */
public class CallRecorderModule extends ReactContextBaseJavaModule {

    private MediaRecorder recorder;
    private String currentFilePath;
    private boolean isCurrentlyRecording = false;

    public CallRecorderModule(ReactApplicationContext reactContext) {
        super(reactContext);
    }

    @Override
    public String getName() {
        return "CallRecorderModule";
    }

    /**
     * Start recording using VOICE_CALL audio source (captures both sides).
     */
    @ReactMethod
    public void startRecording(String phoneNumber, Promise promise) {
        startRecordingWithSource(MediaRecorder.AudioSource.VOICE_CALL, phoneNumber, promise);
    }

    /**
     * Start recording using MIC audio source (captures user side only).
     * Used as fallback when VOICE_CALL is not supported by the device.
     */
    @ReactMethod
    public void startRecordingMic(String phoneNumber, Promise promise) {
        startRecordingWithSource(MediaRecorder.AudioSource.MIC, phoneNumber, promise);
    }

    /**
     * Stop the current recording and return the file path.
     */
    @ReactMethod
    public void stopRecording(Promise promise) {
        if (!isCurrentlyRecording || recorder == null) {
            promise.reject("NOT_RECORDING", "No active recording to stop");
            return;
        }

        try {
            recorder.stop();
            recorder.release();
            recorder = null;
            isCurrentlyRecording = false;

            WritableMap result = Arguments.createMap();
            result.putString("filePath", currentFilePath);
            result.putString("status", "stopped");
            promise.resolve(result);

        } catch (Exception e) {
            recorder = null;
            isCurrentlyRecording = false;
            promise.reject("STOP_FAILED", "Failed to stop recording: " + e.getMessage());
        }
    }

    /**
     * Check if a recording is currently active.
     */
    @ReactMethod
    public void isRecording(Promise promise) {
        promise.resolve(isCurrentlyRecording);
    }

    // ── Internal ─────────────────────────────────────────────────────

    private void startRecordingWithSource(int audioSource, String phoneNumber, Promise promise) {
        ReactApplicationContext context = getReactApplicationContext();

        // Check RECORD_AUDIO permission
        if (ActivityCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            promise.reject("PERMISSION_DENIED", "RECORD_AUDIO permission not granted");
            return;
        }

        // Stop any existing recording
        if (isCurrentlyRecording && recorder != null) {
            try {
                recorder.stop();
                recorder.release();
            } catch (Exception ignored) {}
            recorder = null;
            isCurrentlyRecording = false;
        }

        try {
            // Create output directory
            File outputDir = new File(
                context.getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS),
                "CallCoachRecordings"
            );
            if (!outputDir.exists()) {
                outputDir.mkdirs();
            }

            // Generate filename: call_+919876543210_20260308_143022.m4a
            String cleanNumber = phoneNumber.replaceAll("[^\\d+]", "");
            String timestamp = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(new Date());
            String filename = "call_" + cleanNumber + "_" + timestamp + ".m4a";
            currentFilePath = new File(outputDir, filename).getAbsolutePath();

            // Configure MediaRecorder
            recorder = new MediaRecorder();
            recorder.setAudioSource(audioSource);
            recorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4);
            recorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC);
            recorder.setAudioSamplingRate(16000);  // 16kHz - optimal for speech/Whisper
            recorder.setAudioChannels(1);           // Mono
            recorder.setAudioEncodingBitRate(128000); // 128kbps
            recorder.setOutputFile(currentFilePath);

            recorder.prepare();
            recorder.start();
            isCurrentlyRecording = true;

            WritableMap result = Arguments.createMap();
            result.putString("filePath", currentFilePath);
            result.putString("status", "recording");
            promise.resolve(result);

        } catch (Exception e) {
            recorder = null;
            isCurrentlyRecording = false;
            promise.reject(
                "RECORDING_FAILED",
                "Failed to start recording with source " + audioSource + ": " + e.getMessage()
            );
        }
    }
}

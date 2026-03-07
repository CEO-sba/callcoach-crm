package com.callcoachmobile;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.telephony.TelephonyManager;

import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;
import com.facebook.react.bridge.WritableMap;
import com.facebook.react.bridge.Arguments;
import com.facebook.react.modules.core.DeviceEventManagerModule;

import javax.annotation.Nullable;

/**
 * Native module that monitors phone call state changes and emits events to React Native.
 *
 * Events emitted:
 * - "onCallStateChanged" with payload { state: "callRinging" | "callConnected" | "callEnded", number: string | null }
 *
 * This allows the React Native layer to:
 * - Auto-start recording when a call connects
 * - Auto-stop recording when a call ends
 * - Update the UI with call state
 */
public class CallStateModule extends ReactContextBaseJavaModule {

    private BroadcastReceiver phoneStateReceiver;
    private boolean isListening = false;
    private String lastState = "";

    public CallStateModule(ReactApplicationContext reactContext) {
        super(reactContext);
    }

    @Override
    public String getName() {
        return "CallStateModule";
    }

    /**
     * Start listening for call state changes.
     * Called automatically when the app mounts the ActiveCallScreen.
     */
    @ReactMethod
    public void startListening() {
        if (isListening) return;

        ReactApplicationContext context = getReactApplicationContext();

        phoneStateReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                if (!TelephonyManager.ACTION_PHONE_STATE_CHANGED.equals(intent.getAction())) {
                    return;
                }

                String stateStr = intent.getStringExtra(TelephonyManager.EXTRA_STATE);
                String number = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER);

                if (stateStr == null) return;

                String eventState;
                switch (stateStr) {
                    case TelephonyManager.EXTRA_STATE_RINGING:
                        eventState = "callRinging";
                        break;
                    case TelephonyManager.EXTRA_STATE_OFFHOOK:
                        eventState = "callConnected";
                        break;
                    case TelephonyManager.EXTRA_STATE_IDLE:
                        eventState = "callEnded";
                        break;
                    default:
                        return;
                }

                // Avoid duplicate events
                if (eventState.equals(lastState)) return;
                lastState = eventState;

                emitEvent(eventState, number);
            }
        };

        IntentFilter filter = new IntentFilter(TelephonyManager.ACTION_PHONE_STATE_CHANGED);
        context.registerReceiver(phoneStateReceiver, filter);
        isListening = true;
    }

    /**
     * Stop listening for call state changes.
     */
    @ReactMethod
    public void stopListening() {
        if (!isListening || phoneStateReceiver == null) return;

        try {
            getReactApplicationContext().unregisterReceiver(phoneStateReceiver);
        } catch (Exception ignored) {}

        phoneStateReceiver = null;
        isListening = false;
        lastState = "";
    }

    @Override
    public void onCatalystInstanceDestroy() {
        stopListening();
    }

    // ── Internal ─────────────────────────────────────────────────────

    private void emitEvent(String state, @Nullable String number) {
        ReactApplicationContext context = getReactApplicationContext();
        if (!context.hasActiveReactInstance()) return;

        WritableMap params = Arguments.createMap();
        params.putString("state", state);
        params.putString("number", number);

        context
            .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter.class)
            .emit("onCallStateChanged", params);
    }

    /**
     * Required for NativeEventEmitter on iOS side (no-op here).
     */
    @ReactMethod
    public void addListener(String eventName) {
        // No-op: required for RN NativeEventEmitter
    }

    @ReactMethod
    public void removeListeners(int count) {
        // No-op: required for RN NativeEventEmitter
    }
}

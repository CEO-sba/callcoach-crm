package com.callcoachmobile;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;

import androidx.core.app.ActivityCompat;

import com.facebook.react.bridge.Promise;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;

/**
 * Native module for initiating phone calls via the device's SIM card.
 * Uses Intent.ACTION_CALL to directly place the call (requires CALL_PHONE permission).
 */
public class DialerModule extends ReactContextBaseJavaModule {

    public DialerModule(ReactApplicationContext reactContext) {
        super(reactContext);
    }

    @Override
    public String getName() {
        return "DialerModule";
    }

    /**
     * Initiate a phone call using the device's SIM card.
     *
     * @param phoneNumber Phone number to call (digits and + only)
     * @param promise     Resolves when call intent is dispatched, rejects on error
     */
    @ReactMethod
    public void makeCall(String phoneNumber, Promise promise) {
        try {
            ReactApplicationContext context = getReactApplicationContext();

            // Check CALL_PHONE permission
            if (ActivityCompat.checkSelfPermission(context, Manifest.permission.CALL_PHONE)
                    != PackageManager.PERMISSION_GRANTED) {
                promise.reject("PERMISSION_DENIED", "CALL_PHONE permission not granted");
                return;
            }

            // Clean the phone number - keep only digits and +
            String cleaned = phoneNumber.replaceAll("[^\\d+]", "");
            if (cleaned.isEmpty()) {
                promise.reject("INVALID_NUMBER", "Phone number is empty after cleaning");
                return;
            }

            // Create the call intent
            Intent callIntent = new Intent(Intent.ACTION_CALL);
            callIntent.setData(Uri.parse("tel:" + cleaned));
            callIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

            context.startActivity(callIntent);
            promise.resolve(null);

        } catch (Exception e) {
            promise.reject("CALL_FAILED", "Failed to initiate call: " + e.getMessage());
        }
    }
}

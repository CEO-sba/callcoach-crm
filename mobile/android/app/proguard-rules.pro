# React Native ProGuard Rules

# Keep React Native classes
-keep class com.facebook.hermes.** { *; }
-keep class com.facebook.jni.** { *; }
-keep class com.facebook.react.** { *; }

# Keep our native modules
-keep class com.callcoachmobile.** { *; }

# OkHttp
-keepattributes Signature
-keepattributes *Annotation*
-keep class okhttp3.** { *; }
-keep interface okhttp3.** { *; }
-dontwarn okhttp3.**
-dontwarn okio.**

# React Native Navigation
-keep class com.swmansion.** { *; }
-keep class com.th3rdwave.** { *; }

# Vector Icons
-keep class com.oblador.vectoricons.** { *; }

# Keychain
-keep class com.oblador.keychain.** { *; }

# RNFS
-keep class com.rnfs.** { *; }

# General
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile
-keep public class * extends android.app.Activity
-keep public class * extends android.app.Application
-keep public class * extends android.app.Service
-keep public class * extends android.content.BroadcastReceiver

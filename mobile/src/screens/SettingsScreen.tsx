import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  Switch,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  TextInput,
  ActivityIndicator,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useAppDispatch, useAppSelector } from '../store/store';
import { logout } from '../store/authSlice';
import { setAutoRecord, setWifiOnlyUpload } from '../store/recordingSlice';
import { recordingManager } from '../services/recording';
import api from '../services/api';

function SettingRow({
  icon,
  label,
  description,
  right,
}: {
  icon: string;
  label: string;
  description?: string;
  right: React.ReactNode;
}) {
  return (
    <View style={styles.settingRow}>
      <Icon name={icon} size={22} color="#64748B" style={styles.settingIcon} />
      <View style={styles.settingContent}>
        <Text style={styles.settingLabel}>{label}</Text>
        {description && (
          <Text style={styles.settingDescription}>{description}</Text>
        )}
      </View>
      {right}
    </View>
  );
}

export default function SettingsScreen() {
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);
  const { autoRecord, wifiOnlyUpload, uploadQueue } = useAppSelector(
    (state) => state.recording
  );

  const pendingUploads = uploadQueue.filter((u) => u.status !== 'success');
  const failedUploads = uploadQueue.filter((u) => u.status === 'failed');

  // GHL Integration state
  const [ghlApiKey, setGhlApiKey] = useState('');
  const [ghlLocationId, setGhlLocationId] = useState('');
  const [ghlStatus, setGhlStatus] = useState<any>(null);
  const [ghlLoading, setGhlLoading] = useState(false);
  const [ghlSyncing, setGhlSyncing] = useState(false);
  const [ghlError, setGhlError] = useState('');

  useEffect(() => {
    fetchGHLStatus();
  }, []);

  const fetchGHLStatus = async () => {
    try {
      const res = await api.get('/api/integrations/ghl/status');
      setGhlStatus(res.data);
    } catch {
      setGhlStatus(null);
    }
  };

  const handleGHLConnect = async () => {
    if (!ghlApiKey.trim()) {
      setGhlError('Please enter your GoHighLevel API key');
      return;
    }
    setGhlLoading(true);
    setGhlError('');
    try {
      await api.post('/api/integrations/ghl/connect', {
        api_key: ghlApiKey.trim(),
        location_id: ghlLocationId.trim() || undefined,
      });
      setGhlApiKey('');
      setGhlLocationId('');
      await fetchGHLStatus();
      Alert.alert('Connected', 'GoHighLevel integration connected successfully.');
    } catch (err: any) {
      setGhlError(err.response?.data?.detail || 'Failed to connect');
    } finally {
      setGhlLoading(false);
    }
  };

  const handleGHLDisconnect = () => {
    Alert.alert('Disconnect', 'Remove GoHighLevel integration? Synced leads will be kept.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Disconnect',
        style: 'destructive',
        onPress: async () => {
          try {
            await api.post('/api/integrations/ghl/disconnect');
            setGhlStatus(null);
          } catch {}
        },
      },
    ]);
  };

  const handleGHLSync = async () => {
    setGhlSyncing(true);
    try {
      const res = await api.post('/api/integrations/ghl/sync');
      const d = res.data;
      Alert.alert('Sync Complete', `Created: ${d.created}, Updated: ${d.updated}, Skipped: ${d.skipped}`);
      await fetchGHLStatus();
    } catch (err: any) {
      Alert.alert('Sync Failed', err.response?.data?.detail || 'Could not sync leads');
    } finally {
      setGhlSyncing(false);
    }
  };

  const handleLogout = () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign Out',
        style: 'destructive',
        onPress: () => dispatch(logout()),
      },
    ]);
  };

  const handleRetryAll = () => {
    failedUploads.forEach((item) => {
      recordingManager.retryRecording(item.id);
    });
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Profile Card */}
      <View style={styles.profileCard}>
        <View style={styles.profileAvatar}>
          <Text style={styles.profileAvatarText}>
            {user?.full_name?.charAt(0).toUpperCase() || '?'}
          </Text>
        </View>
        <View>
          <Text style={styles.profileName}>{user?.full_name || 'User'}</Text>
          <Text style={styles.profileEmail}>{user?.email}</Text>
          <Text style={styles.profileClinic}>{user?.clinic_name}</Text>
        </View>
      </View>

      {/* Recording Settings */}
      <Text style={styles.sectionTitle}>Recording</Text>
      <View style={styles.sectionCard}>
        <SettingRow
          icon="fiber-manual-record"
          label="Auto-Record Calls"
          description="Automatically start recording when a call connects"
          right={
            <Switch
              value={autoRecord}
              onValueChange={(v) => dispatch(setAutoRecord(v))}
              trackColor={{ false: '#334155', true: '#3B82F680' }}
              thumbColor={autoRecord ? '#3B82F6' : '#64748B'}
            />
          }
        />
        <View style={styles.divider} />
        <SettingRow
          icon="wifi"
          label="Upload on WiFi Only"
          description="Wait for WiFi before uploading recordings"
          right={
            <Switch
              value={wifiOnlyUpload}
              onValueChange={(v) => dispatch(setWifiOnlyUpload(v))}
              trackColor={{ false: '#334155', true: '#3B82F680' }}
              thumbColor={wifiOnlyUpload ? '#3B82F6' : '#64748B'}
            />
          }
        />
      </View>

      {/* Upload Queue */}
      <Text style={styles.sectionTitle}>Upload Queue</Text>
      <View style={styles.sectionCard}>
        <SettingRow
          icon="cloud-queue"
          label="Pending Uploads"
          right={
            <Text style={styles.statText}>
              {pendingUploads.length}
            </Text>
          }
        />
        {failedUploads.length > 0 && (
          <>
            <View style={styles.divider} />
            <SettingRow
              icon="error-outline"
              label="Failed Uploads"
              right={
                <TouchableOpacity
                  style={styles.retryButton}
                  onPress={handleRetryAll}
                >
                  <Text style={styles.retryText}>Retry All</Text>
                </TouchableOpacity>
              }
            />
          </>
        )}
      </View>

      {/* GoHighLevel Integration */}
      <Text style={styles.sectionTitle}>GoHighLevel</Text>
      <View style={styles.sectionCard}>
        {ghlStatus?.is_connected ? (
          <>
            <SettingRow
              icon="link"
              label="Connected"
              description={`${ghlStatus.total_leads_synced || 0} leads synced`}
              right={
                <View style={styles.connectedBadge}>
                  <Text style={styles.connectedText}>Active</Text>
                </View>
              }
            />
            <View style={styles.divider} />
            <SettingRow
              icon="sync"
              label="Last Sync"
              description={ghlStatus.last_sync_status || 'Never'}
              right={
                <TouchableOpacity
                  style={styles.syncButton}
                  onPress={handleGHLSync}
                  disabled={ghlSyncing}
                >
                  {ghlSyncing ? (
                    <ActivityIndicator size="small" color="#3B82F6" />
                  ) : (
                    <Text style={styles.syncText}>Sync Now</Text>
                  )}
                </TouchableOpacity>
              }
            />
            <View style={styles.divider} />
            <TouchableOpacity
              style={styles.disconnectRow}
              onPress={handleGHLDisconnect}
            >
              <Icon name="link-off" size={18} color="#EF4444" />
              <Text style={styles.disconnectText}>Disconnect</Text>
            </TouchableOpacity>
          </>
        ) : (
          <View style={styles.ghlConnectForm}>
            <Text style={styles.ghlFormLabel}>API Key</Text>
            <TextInput
              style={styles.ghlInput}
              value={ghlApiKey}
              onChangeText={setGhlApiKey}
              placeholder="Enter GoHighLevel API key"
              placeholderTextColor="#475569"
              secureTextEntry
              autoCapitalize="none"
            />
            <Text style={styles.ghlFormLabel}>Location ID (optional)</Text>
            <TextInput
              style={styles.ghlInput}
              value={ghlLocationId}
              onChangeText={setGhlLocationId}
              placeholder="Sub-account location ID"
              placeholderTextColor="#475569"
              autoCapitalize="none"
            />
            {ghlError ? (
              <Text style={styles.ghlErrorText}>{ghlError}</Text>
            ) : null}
            <TouchableOpacity
              style={styles.ghlConnectButton}
              onPress={handleGHLConnect}
              disabled={ghlLoading}
            >
              {ghlLoading ? (
                <ActivityIndicator size="small" color="#FFF" />
              ) : (
                <Text style={styles.ghlConnectButtonText}>Connect</Text>
              )}
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* About */}
      <Text style={styles.sectionTitle}>About</Text>
      <View style={styles.sectionCard}>
        <SettingRow
          icon="info-outline"
          label="Version"
          right={<Text style={styles.statText}>1.0.0</Text>}
        />
        <View style={styles.divider} />
        <SettingRow
          icon="language"
          label="Server"
          right={
            <Text style={styles.statText} numberOfLines={1}>
              callcoachsba.com
            </Text>
          }
        />
      </View>

      {/* Logout */}
      <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
        <Icon name="logout" size={20} color="#EF4444" />
        <Text style={styles.logoutText}>Sign Out</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F172A' },
  content: { padding: 16, paddingBottom: 40 },
  profileCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1E293B',
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: '#334155',
    gap: 16,
  },
  profileAvatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#3B82F6',
    justifyContent: 'center',
    alignItems: 'center',
  },
  profileAvatarText: { color: '#FFF', fontSize: 22, fontWeight: '600' },
  profileName: { color: '#F8FAFC', fontSize: 18, fontWeight: '700' },
  profileEmail: { color: '#94A3B8', fontSize: 13, marginTop: 2 },
  profileClinic: { color: '#3B82F6', fontSize: 13, marginTop: 2 },
  sectionTitle: {
    color: '#64748B',
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 8,
    marginLeft: 4,
  },
  sectionCard: {
    backgroundColor: '#1E293B',
    borderRadius: 16,
    paddingVertical: 4,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: '#334155',
  },
  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  settingIcon: { marginRight: 12 },
  settingContent: { flex: 1 },
  settingLabel: { color: '#F8FAFC', fontSize: 15 },
  settingDescription: { color: '#64748B', fontSize: 12, marginTop: 2 },
  divider: {
    height: 1,
    backgroundColor: '#334155',
    marginHorizontal: 16,
  },
  statText: { color: '#94A3B8', fontSize: 15 },
  retryButton: {
    backgroundColor: '#F59E0B20',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  retryText: { color: '#F59E0B', fontSize: 13, fontWeight: '600' },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1E293B',
    borderRadius: 12,
    paddingVertical: 16,
    gap: 8,
    borderWidth: 1,
    borderColor: '#7F1D1D',
  },
  logoutText: { color: '#EF4444', fontSize: 16, fontWeight: '600' },
  connectedBadge: {
    backgroundColor: '#10B98120',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  connectedText: { color: '#10B981', fontSize: 13, fontWeight: '600' },
  syncButton: {
    backgroundColor: '#3B82F620',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    minWidth: 80,
    alignItems: 'center',
  },
  syncText: { color: '#3B82F6', fontSize: 13, fontWeight: '600' },
  disconnectRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    gap: 6,
  },
  disconnectText: { color: '#EF4444', fontSize: 14, fontWeight: '500' },
  ghlConnectForm: { padding: 16 },
  ghlFormLabel: {
    color: '#94A3B8',
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 6,
    marginTop: 8,
  },
  ghlInput: {
    backgroundColor: '#0F172A',
    borderWidth: 1,
    borderColor: '#334155',
    borderRadius: 10,
    padding: 12,
    color: '#F8FAFC',
    fontSize: 14,
  },
  ghlErrorText: { color: '#EF4444', fontSize: 12, marginTop: 8 },
  ghlConnectButton: {
    backgroundColor: '#3B82F6',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 16,
  },
  ghlConnectButtonText: { color: '#FFF', fontSize: 15, fontWeight: '700' },
});

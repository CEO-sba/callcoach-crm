import React, { useEffect, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useAppDispatch, useAppSelector } from '../store/store';
import { fetchCalls, Call } from '../store/callsSlice';
import { RootStackParamList } from '../navigation/RootNavigator';

type NavProp = NativeStackNavigationProp<RootStackParamList>;

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return d.toLocaleDateString([], { weekday: 'short' });
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function getScoreColor(score: number | null): string {
  if (!score) return '#64748B';
  if (score >= 80) return '#22C55E';
  if (score >= 60) return '#F59E0B';
  return '#EF4444';
}

function getStatusIcon(status: string): { icon: string; color: string } {
  switch (status) {
    case 'completed':
      return { icon: 'check-circle', color: '#22C55E' };
    case 'processing':
    case 'transcribing':
      return { icon: 'hourglass-empty', color: '#F59E0B' };
    case 'failed':
      return { icon: 'error', color: '#EF4444' };
    default:
      return { icon: 'schedule', color: '#64748B' };
  }
}

function CallCard({ call }: { call: Call }) {
  const navigation = useNavigation<NavProp>();
  const statusInfo = getStatusIcon(call.transcription_status);

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={() =>
        navigation.navigate('CallDetail', {
          callId: call.id,
          callerName: call.caller_name,
        })
      }
    >
      <View style={styles.cardLeft}>
        <View style={styles.directionIcon}>
          <Icon
            name={call.direction === 'inbound' ? 'call-received' : 'call-made'}
            size={18}
            color={call.direction === 'inbound' ? '#3B82F6' : '#22C55E'}
          />
        </View>
      </View>

      <View style={styles.cardContent}>
        <Text style={styles.callerName}>{call.caller_name}</Text>
        <Text style={styles.callerPhone}>{call.caller_phone}</Text>
        <View style={styles.metaRow}>
          <Text style={styles.metaText}>
            {formatDuration(call.duration_seconds)}
          </Text>
          <Text style={styles.metaDot}>.</Text>
          <Text style={styles.metaText}>{call.call_type}</Text>
          <Icon
            name={statusInfo.icon}
            size={14}
            color={statusInfo.color}
            style={{ marginLeft: 8 }}
          />
        </View>
      </View>

      <View style={styles.cardRight}>
        <Text style={styles.dateText}>{formatDate(call.created_at)}</Text>
        {call.ai_score !== null && (
          <View
            style={[
              styles.scoreBadge,
              { backgroundColor: getScoreColor(call.ai_score) + '20' },
            ]}
          >
            <Text
              style={[
                styles.scoreText,
                { color: getScoreColor(call.ai_score) },
              ]}
            >
              {call.ai_score}
            </Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );
}

export default function CallHistoryScreen() {
  const dispatch = useAppDispatch();
  const { calls, isLoading } = useAppSelector((state) => state.calls);
  const { uploadQueue } = useAppSelector((state) => state.recording);

  useEffect(() => {
    dispatch(fetchCalls());
  }, [dispatch]);

  const onRefresh = useCallback(() => {
    dispatch(fetchCalls());
  }, [dispatch]);

  const pendingUploads = uploadQueue.filter(
    (u) => u.status !== 'success'
  );

  return (
    <View style={styles.container}>
      {/* Pending Uploads Banner */}
      {pendingUploads.length > 0 && (
        <View style={styles.uploadBanner}>
          <Icon name="cloud-upload" size={18} color="#F59E0B" />
          <Text style={styles.uploadBannerText}>
            {pendingUploads.length} recording{pendingUploads.length !== 1 ? 's' : ''} pending upload
          </Text>
        </View>
      )}

      {isLoading && calls.length === 0 ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#3B82F6" />
        </View>
      ) : (
        <FlatList
          data={calls}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <CallCard call={item} />}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={isLoading}
              onRefresh={onRefresh}
              tintColor="#3B82F6"
            />
          }
          ListEmptyComponent={
            <View style={styles.center}>
              <Icon name="call" size={48} color="#334155" />
              <Text style={styles.emptyText}>No calls yet</Text>
              <Text style={styles.emptySubtext}>
                Make your first call from Contacts or the Dialer
              </Text>
            </View>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F172A' },
  uploadBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#422006',
    paddingHorizontal: 16,
    paddingVertical: 10,
    gap: 8,
  },
  uploadBannerText: { color: '#F59E0B', fontSize: 13, fontWeight: '500' },
  list: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 16 },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1E293B',
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#334155',
  },
  cardLeft: { marginRight: 12 },
  directionIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#0F172A',
    justifyContent: 'center',
    alignItems: 'center',
  },
  cardContent: { flex: 1 },
  callerName: { color: '#F8FAFC', fontSize: 15, fontWeight: '600' },
  callerPhone: { color: '#94A3B8', fontSize: 12, marginTop: 2 },
  metaRow: { flexDirection: 'row', alignItems: 'center', marginTop: 4 },
  metaText: { color: '#64748B', fontSize: 12 },
  metaDot: { color: '#64748B', marginHorizontal: 4 },
  cardRight: { alignItems: 'flex-end' },
  dateText: { color: '#64748B', fontSize: 12, marginBottom: 4 },
  scoreBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
  },
  scoreText: { fontSize: 14, fontWeight: '700' },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 80,
  },
  emptyText: { color: '#64748B', fontSize: 16, marginTop: 12 },
  emptySubtext: { color: '#475569', fontSize: 13, marginTop: 4, textAlign: 'center' },
});

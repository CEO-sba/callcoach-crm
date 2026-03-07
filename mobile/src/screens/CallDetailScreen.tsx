import React, { useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useRoute, RouteProp } from '@react-navigation/native';
import { useAppDispatch, useAppSelector } from '../store/store';
import { fetchCallDetail, clearSelectedCall } from '../store/callsSlice';
import { RootStackParamList } from '../navigation/RootNavigator';

type DetailRouteProp = RouteProp<RootStackParamList, 'CallDetail'>;

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 80 ? '#22C55E' : score >= 60 ? '#F59E0B' : '#EF4444';
  return (
    <View style={[styles.scoreBadge, { borderColor: color }]}>
      <Text style={[styles.scoreValue, { color }]}>{score}</Text>
      <Text style={styles.scoreLabel}>AI Score</Text>
    </View>
  );
}

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon: string;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <Icon name={icon} size={18} color="#3B82F6" />
        <Text style={styles.sectionTitle}>{title}</Text>
      </View>
      {children}
    </View>
  );
}

export default function CallDetailScreen() {
  const route = useRoute<DetailRouteProp>();
  const dispatch = useAppDispatch();
  const { selectedCall, isLoadingDetail } = useAppSelector((state) => state.calls);

  const { callId } = route.params;

  useEffect(() => {
    dispatch(fetchCallDetail(callId));
    return () => {
      dispatch(clearSelectedCall());
    };
  }, [dispatch, callId]);

  if (isLoadingDetail || !selectedCall) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#3B82F6" />
        <Text style={styles.loadingText}>Loading analysis...</Text>
      </View>
    );
  }

  const call = selectedCall;
  const durationMin = Math.floor(call.duration_seconds / 60);
  const durationSec = call.duration_seconds % 60;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Header Card */}
      <View style={styles.headerCard}>
        <View style={styles.headerTop}>
          <View>
            <Text style={styles.callerName}>{call.caller_name}</Text>
            <Text style={styles.callerPhone}>{call.caller_phone}</Text>
          </View>
          {call.ai_score !== null && <ScoreBadge score={call.ai_score} />}
        </View>

        <View style={styles.headerMeta}>
          <View style={styles.metaItem}>
            <Icon name="schedule" size={14} color="#64748B" />
            <Text style={styles.metaText}>
              {durationMin}m {durationSec}s
            </Text>
          </View>
          <View style={styles.metaItem}>
            <Icon
              name={call.direction === 'inbound' ? 'call-received' : 'call-made'}
              size={14}
              color="#64748B"
            />
            <Text style={styles.metaText}>{call.direction}</Text>
          </View>
          <View style={styles.metaItem}>
            <Icon name="label" size={14} color="#64748B" />
            <Text style={styles.metaText}>{call.call_type}</Text>
          </View>
        </View>

        {call.ai_sentiment && (
          <View style={styles.sentimentRow}>
            <Text style={styles.sentimentLabel}>Sentiment:</Text>
            <Text style={styles.sentimentValue}>{call.ai_sentiment}</Text>
          </View>
        )}

        {call.ai_intent && (
          <View style={styles.sentimentRow}>
            <Text style={styles.sentimentLabel}>Intent:</Text>
            <Text style={styles.sentimentValue}>{call.ai_intent}</Text>
          </View>
        )}
      </View>

      {/* AI Summary */}
      {call.ai_summary && (
        <Section title="AI Summary" icon="auto-awesome">
          <Text style={styles.bodyText}>{call.ai_summary}</Text>
        </Section>
      )}

      {/* Key Topics */}
      {call.ai_key_topics && call.ai_key_topics.length > 0 && (
        <Section title="Key Topics" icon="topic">
          <View style={styles.tagContainer}>
            {call.ai_key_topics.map((topic, i) => (
              <View key={i} style={styles.tag}>
                <Text style={styles.tagText}>{topic}</Text>
              </View>
            ))}
          </View>
        </Section>
      )}

      {/* Action Items */}
      {call.ai_action_items && call.ai_action_items.length > 0 && (
        <Section title="Action Items" icon="checklist">
          {call.ai_action_items.map((item, i) => (
            <View key={i} style={styles.listItem}>
              <Icon name="arrow-right" size={14} color="#3B82F6" />
              <Text style={styles.listItemText}>{item}</Text>
            </View>
          ))}
        </Section>
      )}

      {/* Coaching Tips */}
      {call.ai_coaching_tips && call.ai_coaching_tips.length > 0 && (
        <Section title="Coaching Tips" icon="school">
          {call.ai_coaching_tips.map((tip, i) => (
            <View key={i} style={styles.listItem}>
              <Icon name="lightbulb" size={14} color="#F59E0B" />
              <Text style={styles.listItemText}>{tip}</Text>
            </View>
          ))}
        </Section>
      )}

      {/* Transcription */}
      {call.transcription_text && (
        <Section title="Transcription" icon="subtitles">
          <Text style={styles.transcriptionText}>
            {call.transcription_text}
          </Text>
        </Section>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F172A' },
  content: { padding: 16, paddingBottom: 32 },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0F172A',
  },
  loadingText: { color: '#64748B', marginTop: 12 },
  headerCard: {
    backgroundColor: '#1E293B',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#334155',
  },
  headerTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  callerName: { color: '#F8FAFC', fontSize: 20, fontWeight: '700' },
  callerPhone: { color: '#94A3B8', fontSize: 14, marginTop: 2 },
  scoreBadge: {
    borderWidth: 2,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 6,
    alignItems: 'center',
  },
  scoreValue: { fontSize: 24, fontWeight: '800' },
  scoreLabel: { fontSize: 10, color: '#64748B', marginTop: -2 },
  headerMeta: {
    flexDirection: 'row',
    gap: 16,
    marginTop: 16,
  },
  metaItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  metaText: { color: '#64748B', fontSize: 13 },
  sentimentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    gap: 6,
  },
  sentimentLabel: { color: '#64748B', fontSize: 13 },
  sentimentValue: { color: '#F8FAFC', fontSize: 13, fontWeight: '500' },
  section: {
    backgroundColor: '#1E293B',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#334155',
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  sectionTitle: { color: '#F8FAFC', fontSize: 16, fontWeight: '600' },
  bodyText: { color: '#CBD5E1', fontSize: 14, lineHeight: 22 },
  tagContainer: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  tag: {
    backgroundColor: '#3B82F620',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  tagText: { color: '#3B82F6', fontSize: 13 },
  listItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 8,
  },
  listItemText: { color: '#CBD5E1', fontSize: 14, flex: 1, lineHeight: 20 },
  transcriptionText: {
    color: '#94A3B8',
    fontSize: 13,
    lineHeight: 20,
    fontFamily: 'monospace',
  },
});

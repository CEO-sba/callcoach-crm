import React, { useEffect, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useAppDispatch, useAppSelector } from '../store/store';
import { fetchContacts, syncContacts, setSearchQuery, Contact } from '../store/contactsSlice';
import { MainTabParamList } from '../navigation/RootNavigator';

type NavProp = NativeStackNavigationProp<MainTabParamList, 'Contacts'>;

function getSentimentColor(sentiment: string | null): string {
  if (!sentiment) return '#64748B';
  const s = sentiment.toLowerCase();
  if (s.includes('positive') || s.includes('happy')) return '#22C55E';
  if (s.includes('negative') || s.includes('frustrated')) return '#EF4444';
  return '#F59E0B';
}

function ContactCard({ contact }: { contact: Contact }) {
  const navigation = useNavigation<NavProp>();

  const handleCall = () => {
    navigation.navigate('Dialer', {
      phoneNumber: contact.phone,
      callerName: contact.name,
    });
  };

  return (
    <TouchableOpacity style={styles.card} onPress={handleCall}>
      <View style={styles.avatar}>
        <Text style={styles.avatarText}>
          {contact.name.charAt(0).toUpperCase()}
        </Text>
      </View>
      <View style={styles.cardContent}>
        <Text style={styles.name}>{contact.name}</Text>
        <Text style={styles.phone}>{contact.phone}</Text>
        <View style={styles.meta}>
          {contact.total_calls > 0 && (
            <Text style={styles.metaText}>
              {contact.total_calls} call{contact.total_calls !== 1 ? 's' : ''}
            </Text>
          )}
          {contact.last_sentiment && (
            <View
              style={[
                styles.sentimentBadge,
                { backgroundColor: getSentimentColor(contact.last_sentiment) + '20' },
              ]}
            >
              <Text
                style={[
                  styles.sentimentText,
                  { color: getSentimentColor(contact.last_sentiment) },
                ]}
              >
                {contact.last_sentiment}
              </Text>
            </View>
          )}
        </View>
      </View>
      <TouchableOpacity style={styles.callButton} onPress={handleCall}>
        <Icon name="call" size={22} color="#22C55E" />
      </TouchableOpacity>
    </TouchableOpacity>
  );
}

export default function ContactsScreen() {
  const dispatch = useAppDispatch();
  const { contacts, isLoading, searchQuery } = useAppSelector(
    (state) => state.contacts
  );

  useEffect(() => {
    dispatch(fetchContacts());
  }, [dispatch]);

  // Background sync every 30 seconds for real-time GHL contact updates
  useEffect(() => {
    const interval = setInterval(() => {
      dispatch(syncContacts());
    }, 30000);
    return () => clearInterval(interval);
  }, [dispatch]);

  const onRefresh = useCallback(() => {
    dispatch(fetchContacts());
  }, [dispatch]);

  // Filter contacts locally based on search query
  const displayContacts = searchQuery
    ? (contacts || []).filter((c) => {
        const q = searchQuery.toLowerCase();
        return (
          c.name?.toLowerCase().includes(q) ||
          c.phone?.includes(q) ||
          c.email?.toLowerCase().includes(q)
        );
      })
    : contacts || [];

  return (
    <View style={styles.container}>
      <View style={styles.searchBar}>
        <Icon name="search" size={20} color="#64748B" />
        <TextInput
          style={styles.searchInput}
          placeholder="Search contacts..."
          placeholderTextColor="#64748B"
          value={searchQuery}
          onChangeText={(t) => dispatch(setSearchQuery(t))}
        />
        {searchQuery ? (
          <TouchableOpacity onPress={() => dispatch(setSearchQuery(''))}>
            <Icon name="close" size={20} color="#64748B" />
          </TouchableOpacity>
        ) : null}
      </View>

      {isLoading && (!contacts || contacts.length === 0) ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#3B82F6" />
        </View>
      ) : (
        <FlatList
          data={displayContacts}
          keyExtractor={(item) => item.phone}
          renderItem={({ item }) => <ContactCard contact={item} />}
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
              <Icon name="people-outline" size={48} color="#334155" />
              <Text style={styles.emptyText}>No contacts found</Text>
            </View>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F172A' },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1E293B',
    margin: 16,
    paddingHorizontal: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#334155',
  },
  searchInput: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 8,
    fontSize: 16,
    color: '#F8FAFC',
  },
  list: { paddingHorizontal: 16, paddingBottom: 16 },
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
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#3B82F6',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  avatarText: { color: '#FFF', fontSize: 18, fontWeight: '600' },
  cardContent: { flex: 1 },
  name: { color: '#F8FAFC', fontSize: 16, fontWeight: '600' },
  phone: { color: '#94A3B8', fontSize: 13, marginTop: 2 },
  meta: { flexDirection: 'row', alignItems: 'center', marginTop: 4, gap: 8 },
  metaText: { color: '#64748B', fontSize: 12 },
  sentimentBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
  },
  sentimentText: { fontSize: 11, fontWeight: '500' },
  callButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#22C55E20',
    justifyContent: 'center',
    alignItems: 'center',
  },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingTop: 60 },
  emptyText: { color: '#64748B', fontSize: 16, marginTop: 12 },
});

import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { api } from '../services/api';

export interface Contact {
  name: string;
  phone: string;
  email: string;
  total_calls: number;
  total_deals: number;
  treatments_interested: string[];
  last_sentiment: string;
  last_intent: string;
  deal_stages: string[];
  deal_value: number;
}

interface ContactsState {
  contacts: Contact[];
  isLoading: boolean;
  error: string | null;
  searchQuery: string;
  lastSyncTimestamp: string | null;
}

const initialState: ContactsState = {
  contacts: [],
  isLoading: false,
  error: null,
  searchQuery: '',
  lastSyncTimestamp: null,
};

// Full fetch (initial load or pull-to-refresh)
export const fetchContacts = createAsyncThunk('contacts/fetch', async () => {
  const data = await api.getContacts();
  const contacts = data.contacts || data;
  const timestamp = data.timestamp || null;
  return { contacts, timestamp };
});

// Incremental fetch (background sync - only new/updated contacts)
export const syncContacts = createAsyncThunk(
  'contacts/sync',
  async (_, { getState }) => {
    const state = getState() as { contacts: ContactsState };
    const since = state.contacts.lastSyncTimestamp;
    const params = since ? `?updated_since=${encodeURIComponent(since)}` : '';
    const resp = await api.get(`/contacts${params}`);
    const data = resp.data || resp;
    const contacts = data.contacts || [];
    const timestamp = data.timestamp || null;
    return { contacts, timestamp };
  }
);

const contactsSlice = createSlice({
  name: 'contacts',
  initialState,
  reducers: {
    setSearchQuery: (state, action) => {
      state.searchQuery = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      // Full fetch
      .addCase(fetchContacts.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchContacts.fulfilled, (state, action) => {
        state.isLoading = false;
        const { contacts, timestamp } = action.payload;
        state.contacts = Array.isArray(contacts) ? contacts : [];
        if (timestamp) state.lastSyncTimestamp = timestamp;
      })
      .addCase(fetchContacts.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to load contacts';
      })

      // Incremental sync (background, doesn't show loading)
      .addCase(syncContacts.fulfilled, (state, action) => {
        const { contacts: updated, timestamp } = action.payload;
        if (Array.isArray(updated) && updated.length > 0) {
          // Merge: update existing contacts by phone match, add new ones
          const existingMap = new Map(
            state.contacts.map((c) => [(c.phone || c.email || c.name || '').toLowerCase(), c])
          );
          for (const newContact of updated) {
            const key = (newContact.phone || newContact.email || newContact.name || '').toLowerCase();
            if (key) existingMap.set(key, newContact);
          }
          state.contacts = Array.from(existingMap.values());
        }
        if (timestamp) state.lastSyncTimestamp = timestamp;
      });
  },
});

export const { setSearchQuery } = contactsSlice.actions;
export default contactsSlice.reducer;

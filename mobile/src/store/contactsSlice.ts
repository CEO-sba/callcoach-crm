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
  items: Contact[];
  isLoading: boolean;
  error: string | null;
  searchQuery: string;
}

const initialState: ContactsState = {
  items: [],
  isLoading: false,
  error: null,
  searchQuery: '',
};

export const fetchContacts = createAsyncThunk('contacts/fetch', async () => {
  const data = await api.getContacts();
  return data.contacts || data;
});

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
      .addCase(fetchContacts.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchContacts.fulfilled, (state, action) => {
        state.isLoading = false;
        state.items = action.payload;
      })
      .addCase(fetchContacts.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to load contacts';
      });
  },
});

export const { setSearchQuery } = contactsSlice.actions;
export default contactsSlice.reducer;

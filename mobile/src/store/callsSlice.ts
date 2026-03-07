import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { api } from '../services/api';

export interface Call {
  id: string;
  caller_name: string;
  caller_phone: string;
  call_type: string;
  direction: string;
  duration_seconds: number;
  created_at: string;
  transcription_status: string;
  ai_summary: string | null;
  ai_sentiment: string | null;
  ai_score: number | null;
  recording_url: string | null;
}

export interface CallDetail extends Call {
  transcription_text: string | null;
  ai_key_topics: string[] | null;
  ai_action_items: string[] | null;
  ai_coaching_tips: string[] | null;
  ai_intent: string | null;
  contact_id: string | null;
}

interface CallsState {
  calls: Call[];
  selectedCall: CallDetail | null;
  isLoading: boolean;
  isLoadingDetail: boolean;
  error: string | null;
}

const initialState: CallsState = {
  calls: [],
  selectedCall: null,
  isLoading: false,
  isLoadingDetail: false,
  error: null,
};

export const fetchCalls = createAsyncThunk('calls/fetchAll', async () => {
  return await api.getCalls();
});

export const fetchCallDetail = createAsyncThunk(
  'calls/fetchDetail',
  async (callId: string) => {
    return await api.getCallDetail(callId);
  }
);

const callsSlice = createSlice({
  name: 'calls',
  initialState,
  reducers: {
    clearSelectedCall: (state) => {
      state.selectedCall = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchCalls.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchCalls.fulfilled, (state, action) => {
        state.isLoading = false;
        state.calls = action.payload;
      })
      .addCase(fetchCalls.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to load calls';
      })
      .addCase(fetchCallDetail.pending, (state) => {
        state.isLoadingDetail = true;
      })
      .addCase(fetchCallDetail.fulfilled, (state, action) => {
        state.isLoadingDetail = false;
        state.selectedCall = action.payload;
      })
      .addCase(fetchCallDetail.rejected, (state) => {
        state.isLoadingDetail = false;
      });
  },
});

export const { clearSelectedCall } = callsSlice.actions;
export default callsSlice.reducer;

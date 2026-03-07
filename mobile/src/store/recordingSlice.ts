import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface ActiveCall {
  phoneNumber: string;
  callerName: string;
  startTime: number;
  recordingPath: string | null;
  isRecording: boolean;
  isConnected: boolean;
}

interface UploadItem {
  id: string;
  callerName: string;
  callerPhone: string;
  status: 'pending' | 'uploading' | 'success' | 'failed';
  progress: number;
  errorMessage?: string;
}

interface RecordingState {
  activeCall: ActiveCall | null;
  uploadQueue: UploadItem[];
  autoRecord: boolean;
  wifiOnlyUpload: boolean;
}

const initialState: RecordingState = {
  activeCall: null,
  uploadQueue: [],
  autoRecord: true,
  wifiOnlyUpload: false,
};

const recordingSlice = createSlice({
  name: 'recording',
  initialState,
  reducers: {
    setActiveCall: (state, action: PayloadAction<ActiveCall | null>) => {
      state.activeCall = action.payload;
    },
    updateActiveCall: (state, action: PayloadAction<Partial<ActiveCall>>) => {
      if (state.activeCall) {
        Object.assign(state.activeCall, action.payload);
      }
    },
    addUploadItem: (state, action: PayloadAction<UploadItem>) => {
      state.uploadQueue.push(action.payload);
    },
    updateUploadItem: (
      state,
      action: PayloadAction<{ id: string } & Partial<UploadItem>>
    ) => {
      const item = state.uploadQueue.find((u) => u.id === action.payload.id);
      if (item) {
        Object.assign(item, action.payload);
      }
    },
    removeUploadItem: (state, action: PayloadAction<string>) => {
      state.uploadQueue = state.uploadQueue.filter((u) => u.id !== action.payload);
    },
    clearCompletedUploads: (state) => {
      state.uploadQueue = state.uploadQueue.filter((u) => u.status !== 'success');
    },
    setAutoRecord: (state, action: PayloadAction<boolean>) => {
      state.autoRecord = action.payload;
    },
    setWifiOnlyUpload: (state, action: PayloadAction<boolean>) => {
      state.wifiOnlyUpload = action.payload;
    },
  },
});

export const {
  setActiveCall,
  updateActiveCall,
  addUploadItem,
  updateUploadItem,
  removeUploadItem,
  clearCompletedUploads,
  setAutoRecord,
  setWifiOnlyUpload,
} = recordingSlice.actions;
export default recordingSlice.reducer;

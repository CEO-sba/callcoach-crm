/**
 * CallCoach CRM - API Client
 *
 * Axios-based client for all CallCoach backend communication.
 * Handles JWT auth, multipart recording uploads, and token refresh.
 */
import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import * as Keychain from 'react-native-keychain';

const API_BASE_URL = 'https://www.callcoachsba.com/api';
const TOKEN_KEY = 'callcoach_auth';

class CallCoachAPI {
  private client: AxiosInstance;
  private onUnauthorized: (() => void) | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: { 'Content-Type': 'application/json' },
    });

    // Attach JWT to every request
    this.client.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
      const creds = await Keychain.getGenericPassword({ service: TOKEN_KEY });
      if (creds) {
        config.headers.Authorization = `Bearer ${creds.password}`;
      }
      return config;
    });

    // Handle 401 (token expired)
    this.client.interceptors.response.use(
      (res) => res,
      async (error) => {
        if (error.response?.status === 401) {
          await this.clearToken();
          this.onUnauthorized?.();
        }
        return Promise.reject(error);
      }
    );
  }

  setOnUnauthorized(callback: () => void) {
    this.onUnauthorized = callback;
  }

  // ── Token Management ──────────────────────────────────────────────

  async saveToken(token: string): Promise<void> {
    await Keychain.setGenericPassword('token', token, { service: TOKEN_KEY });
  }

  async getToken(): Promise<string | null> {
    const creds = await Keychain.getGenericPassword({ service: TOKEN_KEY });
    return creds ? creds.password : null;
  }

  async clearToken(): Promise<void> {
    await Keychain.resetGenericPassword({ service: TOKEN_KEY });
  }

  async hasToken(): Promise<boolean> {
    const token = await this.getToken();
    return !!token;
  }

  // ── Auth ───────────────────────────────────────────────────────────

  async login(email: string, password: string) {
    const res = await this.client.post('/auth/login', { email, password });
    const token = res.data.access_token;
    await this.saveToken(token);
    return res.data;
  }

  async register(data: {
    email: string;
    password: string;
    full_name: string;
    clinic_name: string;
  }) {
    const res = await this.client.post('/auth/register-simple', data);
    const token = res.data.access_token;
    await this.saveToken(token);
    return res.data;
  }

  async getMe() {
    const res = await this.client.get('/auth/me');
    return res.data;
  }

  async logout() {
    await this.clearToken();
  }

  // ── Contacts ───────────────────────────────────────────────────────

  async getContacts(search?: string) {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    const res = await this.client.get('/contacts', { params });
    return res.data;
  }

  // ── Calls ──────────────────────────────────────────────────────────

  async getCalls(params?: { call_type?: string; limit?: number; offset?: number }) {
    const res = await this.client.get('/calls', { params });
    return res.data;
  }

  async getCallDetail(callId: string) {
    const res = await this.client.get(`/calls/${callId}`);
    return res.data;
  }

  async getCallAudioUrl(callId: string): Promise<string> {
    const token = await this.getToken();
    return `${API_BASE_URL}/calls/${callId}/audio?token=${token}`;
  }

  /**
   * Upload a recorded call to the backend.
   * This is the main integration point for the native call recorder.
   */
  async uploadRecording(params: {
    filePath: string;
    callerName: string;
    callerPhone: string;
    callType: string;
    direction: 'inbound' | 'outbound';
    durationSeconds: number;
    dealId?: string;
    onProgress?: (percent: number) => void;
  }) {
    const formData = new FormData();

    // Append audio file
    formData.append('file', {
      uri: params.filePath.startsWith('file://') ? params.filePath : `file://${params.filePath}`,
      type: 'audio/mp4', // .m4a is audio/mp4
      name: `call_${Date.now()}.m4a`,
    } as any);

    formData.append('caller_name', params.callerName);
    formData.append('caller_phone', params.callerPhone);
    formData.append('call_type', params.callType);
    formData.append('direction', params.direction);
    formData.append('duration_seconds', String(params.durationSeconds));
    if (params.dealId) {
      formData.append('deal_id', params.dealId);
    }

    const res = await this.client.post('/calls/record', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000, // 2 min for large files
      onUploadProgress: (e) => {
        if (e.total) {
          params.onProgress?.(Math.round((e.loaded * 100) / e.total));
        }
      },
    });

    return res.data;
  }

  /**
   * Poll call status until transcription completes.
   */
  async pollCallUntilReady(
    callId: string,
    intervalMs: number = 3000,
    maxAttempts: number = 60
  ): Promise<any> {
    for (let i = 0; i < maxAttempts; i++) {
      const call = await this.getCallDetail(callId);
      if (call.transcription_status === 'completed' || call.transcription_status === 'failed') {
        return call;
      }
      await new Promise((r) => setTimeout(r, intervalMs));
    }
    throw new Error('Transcription timed out');
  }

  // ── Pipeline ───────────────────────────────────────────────────────

  async getDeals(params?: { stage?: string; status?: string }) {
    const res = await this.client.get('/pipeline/deals', { params });
    return res.data;
  }

  // ── Coaching ───────────────────────────────────────────────────────

  async askCoach(callId: string, question: string) {
    const res = await this.client.post(`/calls/${callId}/ask-coach`, { question });
    return res.data;
  }

  // ── Generic HTTP (used by SettingsScreen for GHL endpoints etc.) ──

  async get(path: string, config?: any) {
    return this.client.get(path, config);
  }

  async post(path: string, data?: any, config?: any) {
    return this.client.post(path, data, config);
  }

  async patch(path: string, data?: any, config?: any) {
    return this.client.patch(path, data, config);
  }
}

export const api = new CallCoachAPI();

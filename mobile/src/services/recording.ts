/**
 * CallCoach CRM - Recording Upload Manager
 *
 * Manages a persistent queue of recorded calls waiting to be uploaded.
 * Handles retry logic, offline scenarios, and background uploads.
 */
import RNFS from 'react-native-fs';
import { api } from './api';

// ── Types ──────────────────────────────────────────────────────────

export interface PendingRecording {
  id: string;
  filePath: string;
  callerName: string;
  callerPhone: string;
  callType: string;
  direction: 'inbound' | 'outbound';
  durationSeconds: number;
  createdAt: number;
  uploadAttempts: number;
  status: 'pending' | 'uploading' | 'success' | 'failed';
  errorMessage?: string;
  serverCallId?: string; // set after successful upload
}

type StatusCallback = (recording: PendingRecording) => void;

// ── Constants ──────────────────────────────────────────────────────

const QUEUE_FILE = `${RNFS.DocumentDirectoryPath}/upload_queue.json`;
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 5000;

// ── Recording Manager ──────────────────────────────────────────────

class RecordingManager {
  private queue: PendingRecording[] = [];
  private isProcessing = false;
  private listeners: StatusCallback[] = [];

  /**
   * Initialize the manager - load any pending uploads from disk.
   * Call this once on app startup.
   */
  async initialize(): Promise<void> {
    try {
      const exists = await RNFS.exists(QUEUE_FILE);
      if (exists) {
        const content = await RNFS.readFile(QUEUE_FILE);
        this.queue = JSON.parse(content);
        // Reset any stuck 'uploading' items back to 'pending'
        this.queue.forEach((r) => {
          if (r.status === 'uploading') r.status = 'pending';
        });
        await this.saveToDisk();
      }
    } catch (error) {
      console.error('Failed to load upload queue:', error);
      this.queue = [];
    }

    // Process any pending uploads
    this.processQueue();
  }

  /**
   * Add a new recording to the upload queue.
   * Automatically triggers upload attempt.
   */
  async addRecording(params: {
    filePath: string;
    callerName: string;
    callerPhone: string;
    callType: string;
    direction: 'inbound' | 'outbound';
    durationSeconds: number;
  }): Promise<PendingRecording> {
    const recording: PendingRecording = {
      id: `rec_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      ...params,
      createdAt: Date.now(),
      uploadAttempts: 0,
      status: 'pending',
    };

    this.queue.push(recording);
    this.notifyListeners(recording);
    await this.saveToDisk();
    this.processQueue();

    return recording;
  }

  /**
   * Retry a failed upload.
   */
  async retryRecording(id: string): Promise<void> {
    const recording = this.queue.find((r) => r.id === id);
    if (recording && recording.status === 'failed') {
      recording.status = 'pending';
      recording.uploadAttempts = 0;
      recording.errorMessage = undefined;
      this.notifyListeners(recording);
      await this.saveToDisk();
      this.processQueue();
    }
  }

  /**
   * Remove a recording from the queue (and delete local file).
   */
  async removeRecording(id: string): Promise<void> {
    const idx = this.queue.findIndex((r) => r.id === id);
    if (idx >= 0) {
      const recording = this.queue[idx];
      // Delete local file if it exists
      try {
        const exists = await RNFS.exists(recording.filePath);
        if (exists) await RNFS.unlink(recording.filePath);
      } catch {}
      this.queue.splice(idx, 1);
      await this.saveToDisk();
    }
  }

  /**
   * Get the current queue state.
   */
  getQueue(): PendingRecording[] {
    return [...this.queue];
  }

  /**
   * Get counts by status.
   */
  getStats(): { pending: number; uploading: number; failed: number; success: number } {
    return {
      pending: this.queue.filter((r) => r.status === 'pending').length,
      uploading: this.queue.filter((r) => r.status === 'uploading').length,
      failed: this.queue.filter((r) => r.status === 'failed').length,
      success: this.queue.filter((r) => r.status === 'success').length,
    };
  }

  /**
   * Subscribe to status changes.
   */
  onStatusChange(callback: StatusCallback): () => void {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== callback);
    };
  }

  // ── Internal ─────────────────────────────────────────────────────

  private async processQueue(): Promise<void> {
    if (this.isProcessing) return;
    this.isProcessing = true;

    try {
      // Process pending items one at a time
      const pendingItems = this.queue.filter((r) => r.status === 'pending');

      for (const recording of pendingItems) {
        await this.uploadSingle(recording);
      }
    } finally {
      this.isProcessing = false;
    }
  }

  private async uploadSingle(recording: PendingRecording): Promise<void> {
    // Check file exists
    const exists = await RNFS.exists(recording.filePath);
    if (!exists) {
      recording.status = 'failed';
      recording.errorMessage = 'Recording file not found on device';
      this.notifyListeners(recording);
      await this.saveToDisk();
      return;
    }

    recording.status = 'uploading';
    recording.uploadAttempts++;
    this.notifyListeners(recording);

    try {
      const result = await api.uploadRecording({
        filePath: recording.filePath,
        callerName: recording.callerName,
        callerPhone: recording.callerPhone,
        callType: recording.callType,
        direction: recording.direction,
        durationSeconds: recording.durationSeconds,
        onProgress: (percent) => {
          // Could emit progress events here
        },
      });

      recording.status = 'success';
      recording.serverCallId = result.id;
      this.notifyListeners(recording);
      await this.saveToDisk();

      // Clean up local file after successful upload
      try {
        await RNFS.unlink(recording.filePath);
      } catch {}
    } catch (error: any) {
      if (recording.uploadAttempts >= MAX_RETRIES) {
        recording.status = 'failed';
        recording.errorMessage = error.message || 'Upload failed after max retries';
      } else {
        recording.status = 'pending'; // Will retry
        recording.errorMessage = error.message;
        // Wait before retry
        await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
      }
      this.notifyListeners(recording);
      await this.saveToDisk();
    }
  }

  private async saveToDisk(): Promise<void> {
    try {
      await RNFS.writeFile(QUEUE_FILE, JSON.stringify(this.queue));
    } catch (error) {
      console.error('Failed to save upload queue:', error);
    }
  }

  private notifyListeners(recording: PendingRecording): void {
    this.listeners.forEach((cb) => cb(recording));
  }
}

export const recordingManager = new RecordingManager();

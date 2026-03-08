import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { api } from '../services/api';

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  clinic_id: string;
  clinic_name: string;
}

interface AuthState {
  user: User | null;
  isLoggedIn: boolean;
  isInitializing: boolean;
  isLoginLoading: boolean;
  error: string | null;
}

const initialState: AuthState = {
  user: null,
  isLoggedIn: false,
  isInitializing: true,
  isLoginLoading: false,
  error: null,
};

/**
 * Validate that a response looks like a real user object.
 * FastAPI sometimes returns error objects like {detail: [{type, loc, msg, input}]}
 * which would pass a simple truthy check but crash if rendered.
 */
function isValidUser(data: any): data is User {
  return (
    data &&
    typeof data === 'object' &&
    typeof data.id === 'string' &&
    typeof data.email === 'string'
  );
}

/**
 * Safely extract an error message string from any error shape.
 * FastAPI returns detail as string or as [{type, loc, msg, input}] array.
 */
function extractErrorMessage(error: any): string {
  if (!error) return 'Unknown error';

  // Network error (no response from server)
  if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
    return 'Cannot connect to server. Check your internet connection.';
  }

  const detail = error.response?.data?.detail;

  // FastAPI string error: {detail: "Invalid credentials"}
  if (typeof detail === 'string') {
    return detail;
  }

  // FastAPI validation error: {detail: [{type, loc, msg, input}]}
  if (Array.isArray(detail) && detail.length > 0) {
    const firstError = detail[0];
    if (firstError && typeof firstError.msg === 'string') {
      return firstError.msg;
    }
    return 'Validation error. Please check your input.';
  }

  // Fallback to error message
  if (typeof error.message === 'string') {
    return error.message;
  }

  return 'Login failed. Please try again.';
}

export const checkAuth = createAsyncThunk('auth/check', async () => {
  try {
    const hasToken = await api.hasToken();
    if (!hasToken) return null;
    try {
      const user = await api.getMe();
      // Validate response is actually a user object, not an error
      if (isValidUser(user)) {
        return user;
      }
      // Server returned something unexpected - clear token and go to login
      await api.clearToken();
      return null;
    } catch {
      await api.clearToken();
      return null;
    }
  } catch (e) {
    console.error('checkAuth error:', e);
    return null;
  }
});

export const login = createAsyncThunk(
  'auth/login',
  async (params: { email: string; password: string }, { rejectWithValue }) => {
    try {
      await api.login(params.email, params.password);
      const user = await api.getMe();
      if (isValidUser(user)) {
        return user;
      }
      return rejectWithValue('Unexpected server response. Please try again.');
    } catch (error: any) {
      return rejectWithValue(extractErrorMessage(error));
    }
  }
);

export const logout = createAsyncThunk('auth/logout', async () => {
  try {
    await api.logout();
  } catch (e) {
    console.error('logout error:', e);
  }
});

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    finishInitializing: (state) => {
      state.isInitializing = false;
    },
  },
  extraReducers: (builder) => {
    builder
      // Check auth (initial app load)
      .addCase(checkAuth.pending, (state) => {
        state.isInitializing = true;
      })
      .addCase(checkAuth.fulfilled, (state, action) => {
        state.isInitializing = false;
        state.user = action.payload;
        state.isLoggedIn = !!action.payload;
      })
      .addCase(checkAuth.rejected, (state) => {
        state.isInitializing = false;
        state.isLoggedIn = false;
      })
      // Login (button press)
      .addCase(login.pending, (state) => {
        state.isLoginLoading = true;
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.isLoginLoading = false;
        state.user = action.payload;
        state.isLoggedIn = true;
        state.error = null;
      })
      .addCase(login.rejected, (state, action) => {
        state.isLoginLoading = false;
        // Ensure error is always a string, never an object
        const payload = action.payload;
        state.error = typeof payload === 'string' ? payload : 'Login failed. Please try again.';
      })
      // Logout
      .addCase(logout.fulfilled, (state) => {
        state.user = null;
        state.isLoggedIn = false;
      });
  },
});

export const { clearError, finishInitializing } = authSlice.actions;
export default authSlice.reducer;

import axios from "axios";

// =========================
// API Configuration
// =========================
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
// Assuming your backend Fast API/Flask application serves API routes under /api
const API_PREFIX = `${API_BASE_URL}/api`; 

// Create axios instance
const api = axios.create({
  baseURL: API_PREFIX,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
});

// Request interceptor for auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
      window.dispatchEvent(new Event('auth_expired'));

      // ✅ Don't redirect if we're already on an auth page
      // ✅ Don't redirect if this is the background /auth/me check
      const isAuthRoute = window.location.pathname.includes('/login') ||
                          window.location.pathname.includes('/signup');
      const isAuthEndpoint = originalRequest.url?.includes('/auth/');

      if (!isAuthRoute && !isAuthEndpoint) {
        window.location.href = '/login?session=expired';
      }
    }

    const errorMessage = error.response?.data?.detail ||
                         error.response?.data?.message ||
                         error.message ||
                         'Network error occurred';

    console.error(`API Error [${error.response?.status || 'No Status'}]:`, errorMessage);

    return Promise.reject({
      message: errorMessage,
      status: error.response?.status,
      data: error.response?.data
    });
  }
);
// =========================
// Helper Functions
// =========================
export const apiGet = (endpoint, params = {}) => 
  api.get(endpoint, { params }).then(res => res.data);

export const apiPost = (endpoint, data = {}, config = {}) => 
  api.post(endpoint, data, config).then(res => res.data);

// =========================
// API Endpoints
// =========================

// Public Endpoints
export const fetchRoot = () => apiGet('/');
export const fetchRays = () => apiGet('/rays');
export const fetchReport = () => apiGet('/report');
export const fetchAbout = () => apiGet('/about');
export const fetchAnalysis = () => apiGet('/analysis');
export const fetchAskDoctor = () => apiGet('/askdoctor');
export const fetchContact = () => apiGet('/contact');

// News
export const fetchNews = (page = 1, category = "health", lang = "en") => 
  apiGet('/news', { page, category, lang });

// MRI Upload
export const uploadMri = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return apiPost('/rays/mri', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};

// CKD Analysis
export const analyzeCKDManual = (data) => apiPost('/analysis/ckd/manual', data);
export const analyzeCKDFile = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return apiPost('/analysis/ckd/file', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};

// =========================
// ASCVD Risk Assessment
// =========================
/**
 * Analyze cardiovascular disease risk based on blood test markers
 * @param {Object} data - Blood test data
 * @param {number} data.blood_glucose - Blood glucose level
 * @param {number} data.HbA1C - HbA1C level
 * @param {number} data.Systolic_BP - Systolic blood pressure
 * @param {number} data.Diastolic_BP - Diastolic blood pressure
 * @param {number} data.LDL - LDL cholesterol
 * @param {number} data.HDL - HDL cholesterol
 * @param {number} data.Triglycerides - Triglycerides level
 * @param {number} data.Haemoglobin - Haemoglobin level
 * @param {number} data.MCV - Mean Corpuscular Volume
 * @returns {Promise} Response with disease prediction and recommendations
 */
export const analyzeASCVDRisk = (data) => {
  console.log('🔄 API Call: analyzeASCVDRisk');
  console.log('📤 Data being sent:', data);
  
  return apiPost('/analysis/ascvd-risk', data)
    .then(response => {
      console.log('✅ API Response:', response);
      return response;
    })
    .catch(error => {
      console.error('❌ API Error:', error);
      throw error;
    });
};

// =========================
// Authentication Functions
// =========================

// Standard Login
export const loginUser = (email, password) =>
  apiPost('/auth/login', { email, password }).then(data => {
    if (data.access_token) {
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
    }
    return data;
  });

// Standard Signup
export const signupUser = (userData) =>
  apiPost('/auth/signup', userData).then(data => {
    if (data.access_token) {
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
    }
    return data;
  });

// Google Authentication (Uses ID Token)
export const googleAuth = (data) =>
  apiPost('/auth/google', data).then(res => {
    if (res.access_token) {
      localStorage.setItem('auth_token', res.access_token);
      localStorage.setItem('user', JSON.stringify(res.user));
    }
    return res;
  });

// Logout
export const logoutUser = async () => {
  try {
    await apiPost('/auth/logout'); 
  } catch (error) {
    console.log('Logout API call failed:', error);
  } finally {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
  }
};

export const getCurrentUser = () => apiGet('/auth/me');

// Auth helpers
export const isAuthenticated = () => {
  const token = localStorage.getItem('auth_token');
  if (!token) return false;
  
  try {
    // JWT expiration check
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
};

export const getAuthToken = () => localStorage.getItem('auth_token');

export const getCurrentUserData = () => {
  try {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  } catch (error) {
    console.error('Error parsing user data:', error);
    return null;
  }
};

export const clearAuthData = () => {
  localStorage.removeItem('auth_token');
  localStorage.removeItem('user');
};

export default api;

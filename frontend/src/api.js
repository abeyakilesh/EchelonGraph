import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000,
});

// JWT interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('echelon_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('echelon_token');
      localStorage.removeItem('echelon_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

// Auth
export const login = (username, password) =>
  api.post('/auth/login', { username, password });
export const getMe = () => api.get('/auth/me');
export const getAuditLog = (limit = 100) => api.get(`/auth/audit-log?limit=${limit}`);

// Dashboard
export const getDashboardStats = () => api.get('/dashboard-stats');
export const getTopRiskCompanies = (limit = 10) => api.get(`/top-risk-companies?limit=${limit}`);
export const getRiskDistribution = () => api.get('/risk-distribution');

// Search
export const searchCompanies = (q) => api.get(`/search?q=${encodeURIComponent(q)}`);

// Data
export const uploadData = (synthetic = true) =>
  api.post(`/upload-data?generate_synthetic=${synthetic}`);
export const getGraphData = (limit = 300) => api.get(`/graph-data?limit=${limit}`);

// Company
export const getCompany = (id) => api.get(`/company/${id}`);
export const getInvestigationSummary = (id) => api.get(`/investigation-summary/${id}`);
export const getFraudSignals = (id) => api.get(`/fraud-signals/${id}`);

// Risk
export const getRiskScore = (id) => api.get(`/risk-score/${id}`);
export const computeAllRiskScores = () => api.post('/compute-risk-scores');
export const getCommunityRisk = () => api.get('/community-risk');

// Analytics
export const getCircularPaths = (id) => api.get(`/circular-paths/${id}`);
export const getAllCircularPaths = () => api.get('/circular-paths');
export const getSuspiciousClusters = () => api.get('/suspicious-clusters');
export const computeFeatures = () => api.post('/compute-features');
export const getShellRisk = (id) => api.get(`/shell-risk/${id}`);

// ML
export const trainModel = (epochs = 100) => api.post(`/ml/train?epochs=${epochs}`);
export const getPrediction = (id) => api.get(`/ml/predict/${id}`);
export const getAllPredictions = () => api.get('/ml/predictions');

// Advanced
export const propagateFraud = (id, risk = 100) =>
  api.post(`/advanced/propagate-fraud/${id}?confirmed_risk=${risk}`);
export const simulateRemoval = (id) =>
  api.post(`/advanced/simulate-removal/${id}`);

// Invoices
export const getAllInvoices = () => api.get('/invoices/all');
export const verifyInvoice = (id) => api.get(`/invoices/verify/${id}`);
export const generateSampleInvoices = () => api.post('/invoices/generate-samples');

export default api;

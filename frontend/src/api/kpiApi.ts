import axios from 'axios';

const API = axios.create({ baseURL: 'http://localhost:8000' });

export const getInstitutions = () => API.get('/api/v1/kpis/institutions');
export const getDashboard = () => API.get('/api/v1/academic/dashboard');
export const getAlerts = (institutionId?: string) =>
  API.get('/api/v1/academic/alerts', { params: institutionId ? { institution_id: institutionId } : {} });
export const getAtRisk = () => API.get('/api/v1/academic/at-risk');
export const getTopPerformers = () => API.get('/api/v1/academic/top-performers');
export const getHistory = (institutionId: string, indicator: string) =>
  API.get(`/api/v1/academic/history/${institutionId}`, { params: { indicator } });
export const getOwnKpis = (institutionId: string) =>
  API.get('/api/v1/academic/own', { params: { institution_id: institutionId } });
export const getPredictions = (institutionId: string, indicator: string) =>
  API.get(`/api/v1/academic/predictions/${institutionId}`, { params: { indicator } });
export const explainWhy = (institutionId: string, indicator: string) =>
  API.post('/api/v1/academic/why', { institution_id: institutionId, indicator });
export const compareInstitutions = (indicator: string) =>
  API.get('/api/v1/academic/compare', { params: { indicator } });
export const submitKpis = (institutionId: string, data: Record<string, unknown>) =>
  API.post('/api/v1/academic/submit', data, { params: { institution_id: institutionId } });

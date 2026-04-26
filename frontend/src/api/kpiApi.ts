import axios from 'axios';
import { api } from './client';

const API = axios.create({ baseURL: 'http://localhost:8001' });

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
  api.post('/api/v1/academic/submit', data, { params: { institution_id: institutionId } });
export const processInstitutionScan = (data: Record<string, unknown>, institutionId?: string) =>
  api.post('/api/v1/academic/process-scan', data, { params: { institution_id: institutionId } });

export const uploadDocument = (file: File, institutionId: string) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/api/v1/documents/upload', formData, {
    params: { institution_id: institutionId },
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};

export const getDocuments = () => api.get('/api/v1/documents');
export const getInstitutionDocuments = (institutionId: string) => 
    api.get(`/api/v1/documents`, { params: { institution_id: institutionId } });

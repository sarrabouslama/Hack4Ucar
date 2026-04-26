import { api } from './client';

export const listDocuments = () => api.get('/api/v1/documents/documents');

export const searchDocuments = (query: string) =>
  api.get('/api/v1/documents/search', { params: { query } });

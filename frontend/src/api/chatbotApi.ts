import { api } from './client';

export interface ChatContextPayload {
  kpi_data?: Record<string, unknown>[];
  document_excerpts?: string[];
  recent_alerts?: string[];
  reporting_period?: string;
  current_date?: string;
  extra_context?: Record<string, unknown>;
}

export interface ChatRequestPayload {
  message: string;
  user_id: string;
  session_id?: string | null;
  session_name?: string;
  domain_context?: string;
  context?: ChatContextPayload;
}

export const listChatSessions = (userId: string) =>
  api.get('/api/v1/chatbot/sessions', { params: { user_id: userId } });

export const getChatSession = (sessionId: string) =>
  api.get(`/api/v1/chatbot/sessions/${sessionId}`);

export const sendChatMessage = (payload: ChatRequestPayload) =>
  api.post('/api/v1/chatbot/chat', payload);

export const getMailLogs = () => api.get('/api/v1/chatbot/mail-logs');

export const triggerAnomalyDetection = () =>
  api.post('/api/v1/chatbot/detect-anomalies');

export const requestDraft = (mailLogId: string) =>
  api.post(`/api/v1/chatbot/propose-draft/${mailLogId}`);

export const confirmMailSend = (mailLogId: string) =>
  api.post(`/api/v1/chatbot/confirm-send/${mailLogId}`);

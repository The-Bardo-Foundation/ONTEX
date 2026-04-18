import axios from 'axios';
import type {
  ApproveBody,
  RejectBody,
  TrialDetail,
  TrialListItem,
  TrialsListResponse,
} from './types';

const API_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const api = axios.create({
  baseURL: API_URL,
});

export interface GetTrialsParams {
  status?: string;
  q?: string;
  ingestion_event?: string;
  sort_by?: string;
  page?: number;
  page_size?: number;
}

export const getReviewQueue = async (): Promise<TrialListItem[]> => {
  const response = await api.get<TrialListItem[]>('/trials/review-queue');
  return response.data;
};

export const getTrial = async (nct_id: string): Promise<TrialDetail> => {
  const response = await api.get<TrialDetail>(`/trials/${nct_id}`);
  return response.data;
};

export const getTrials = async (params: GetTrialsParams = {}): Promise<TrialsListResponse> => {
  const response = await api.get<TrialsListResponse>('/trials', { params });
  return response.data;
};

export const approveTrial = async (nct_id: string, body: ApproveBody): Promise<TrialDetail> => {
  const response = await api.patch<TrialDetail>(`/trials/${nct_id}/approve`, body);
  return response.data;
};

export const rejectTrial = async (nct_id: string, body: RejectBody): Promise<TrialDetail> => {
  const response = await api.patch<TrialDetail>(`/trials/${nct_id}/reject`, body);
  return response.data;
};

export const runIngestion = async (): Promise<{ status: string }> => {
  const response = await api.post<{ status: string }>('/debug/run-ingestion');
  return response.data;
};

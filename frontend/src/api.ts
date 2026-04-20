import axios from 'axios';
import type {
  ApproveBody,
  CustomEdits,
  IrrelevantTrialDetail,
  MarkIrrelevantBody,
  RejectBody,
  TrialDetail,
  TrialListItem,
  TrialsListResponse,
} from './types';

const API_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const api = axios.create({
  baseURL: API_URL,
});

// Token provider set by the ClerkProvider wrapper in App.tsx so the axios
// instance can attach Bearer tokens to protected requests without every
// component needing to handle auth.
let _getToken: (() => Promise<string | null>) | null = null;

export function setTokenProvider(getToken: () => Promise<string | null>): void {
  _getToken = getToken;
}

api.interceptors.request.use(async (config) => {
  if (_getToken) {
    const token = await _getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export interface GetTrialsParams {
  status?: string;
  q?: string;
  ingestion_event?: string;
  phase?: string;
  recruiting_status?: string;
  country?: string;
  age_group?: string;
  sort_by?: string;
  page?: number;
  page_size?: number;
}

export interface TrialFacets {
  countries: string[];
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

export const getTrialFacets = async (): Promise<TrialFacets> => {
  const response = await api.get<TrialFacets>('/trials/facets');
  return response.data;
};

export const approveTrial = async (nct_id: string, body: ApproveBody): Promise<TrialDetail> => {
  const response = await api.patch<TrialDetail>(`/trials/${nct_id}/approve`, body);
  return response.data;
};

export const rejectTrial = async (nct_id: string, body: RejectBody): Promise<IrrelevantTrialDetail> => {
  const response = await api.patch<IrrelevantTrialDetail>(`/trials/${nct_id}/reject`, body);
  return response.data;
};

export interface IrrelevantTrialListItem {
  nct_id: string;
  brief_title: string;
  phase: string | null;
  overall_status: string | null;
  brief_summary: string | null;
  last_update_post_date: string | null;
  ai_relevance_reason: string | null;
  rejected_by: string | null;
  rejected_at: string | null;
}

export interface IrrelevantTrialsListResponse {
  items: IrrelevantTrialListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface GetIrrelevantTrialsParams {
  q?: string;
  sort_by?: string;
  page?: number;
  page_size?: number;
}

export const getIrrelevantTrials = async (params: GetIrrelevantTrialsParams = {}): Promise<IrrelevantTrialsListResponse> => {
  const response = await api.get<IrrelevantTrialsListResponse>('/irrelevant-trials', { params });
  return response.data;
};

export const getIrrelevantTrial = async (nct_id: string): Promise<IrrelevantTrialDetail> => {
  const response = await api.get<IrrelevantTrialDetail>(`/irrelevant-trials/${nct_id}`);
  return response.data;
};

export const restoreIrrelevantTrial = async (nct_id: string): Promise<TrialDetail> => {
  const response = await api.post<TrialDetail>(`/irrelevant-trials/${nct_id}/restore`, {});
  return response.data;
};

export const markTrialIrrelevant = async (nct_id: string, body: MarkIrrelevantBody): Promise<IrrelevantTrialDetail> => {
  const response = await api.post<IrrelevantTrialDetail>(`/trials/${nct_id}/mark-irrelevant`, body);
  return response.data;
};

export const editTrial = async (nct_id: string, body: CustomEdits): Promise<TrialDetail> => {
  const response = await api.patch<TrialDetail>(`/trials/${nct_id}/edit`, body);
  return response.data;
};

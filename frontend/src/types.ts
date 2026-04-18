export type TrialStatus = 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED';
export type IngestionEvent = 'NEW' | 'UPDATED';

export interface TrialListItem {
  nct_id: string;
  brief_title: string;
  phase: string | null;
  status: TrialStatus;
  ingestion_event: IngestionEvent | null;
  last_update_post_date: string | null;
}

export interface TrialDetail {
  nct_id: string;
  status: TrialStatus;
  ingestion_event: IngestionEvent | null;

  // Official fields
  brief_title: string;
  brief_summary: string | null;
  overall_status: string | null;
  phase: string | null;
  study_type: string | null;
  location_country: string | null;
  location_city: string | null;
  minimum_age: string | null;
  maximum_age: string | null;
  central_contact_name: string | null;
  central_contact_phone: string | null;
  central_contact_email: string | null;
  eligibility_criteria: string | null;
  intervention_description: string | null;
  last_update_post_date: string | null;
  key_information: string | null;

  // Custom (AI/admin) fields
  custom_brief_title: string | null;
  custom_brief_summary: string | null;
  custom_overall_status: string | null;
  custom_phase: string | null;
  custom_study_type: string | null;
  custom_location_country: string | null;
  custom_location_city: string | null;
  custom_minimum_age: string | null;
  custom_maximum_age: string | null;
  custom_central_contact_name: string | null;
  custom_central_contact_phone: string | null;
  custom_central_contact_email: string | null;
  custom_eligibility_criteria: string | null;
  custom_intervention_description: string | null;
  custom_last_update_post_date: string | null;

  // AI classification
  ai_relevance_confidence: number | null;
  ai_relevance_reason: string | null;
  ai_relevance_tier: string | null;
  ai_matching_criteria: string | null; // JSON string

  // Workflow tracking
  approved_at: string | null;
  approved_by: string | null;
  previous_approved_at: string | null;
  previous_approved_by: string | null;
  rejected_at: string | null;
  rejected_by: string | null;
  reviewer_notes: string | null;
  previous_official_snapshot: string | null; // JSON string
}

export interface TrialsListResponse {
  items: TrialListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApproveBody {
  username: string;
  reviewer_notes?: string;
  custom_brief_title?: string;
  custom_brief_summary?: string;
  custom_overall_status?: string;
  custom_phase?: string;
  custom_study_type?: string;
  custom_location_country?: string;
  custom_location_city?: string;
  custom_minimum_age?: string;
  custom_maximum_age?: string;
  custom_central_contact_name?: string;
  custom_central_contact_phone?: string;
  custom_central_contact_email?: string;
  custom_eligibility_criteria?: string;
  custom_intervention_description?: string;
  custom_last_update_post_date?: string;
  key_information?: string;
}

export interface RejectBody {
  username: string;
  reviewer_notes?: string;
}

export type CustomEdits = Partial<Omit<ApproveBody, 'username' | 'reviewer_notes'>>;

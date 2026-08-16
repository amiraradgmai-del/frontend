export type User = {
  id: string;
  email: string;
  full_name: string;
  account_tier: "normal" | "plus" | "pro";
  is_active: boolean;
  two_factor_enabled: boolean;
  roles: string[];
  permissions: string[];
  created_at: string;
};

export type Citation = {
  chunk_id: string;
  article_number: string | null;
  score: number;
  source_title: string;
  source_url: string | null;
};

export type AskResponse = {
  conversation_id: string;
  message_id: string;
  answer: string;
  citations: Citation[];
  confidence: number;
  needs_expert: boolean;
  disclaimer: string;
  clarifying_questions: string[];
  escalation_reasons: string[];
  refusal_reason: string | null;
  answer_basis: "dataset" | "general_knowledge" | "casual" | "refusal" | "out_of_scope" | "insufficient_source";
  source_notice: string | null;
  agent: string;
  agent_title: string;
};

export type Conversation = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  confidence: number | null;
  needs_expert: boolean;
  disclaimer: string | null;
  created_at: string;
  citations: Array<{ chunk_id: string; quote: string; score: number; rank: number }>;
};

export type Consultation = {
  id: string;
  source_message_id?: string | null;
  subject: string;
  description: string;
  status: string;
  priority: string;
  resolution: string;
  billing_type?: "free" | "wallet";
  price?: number;
  created_at: string;
  updated_at: string;
  user_id?: string;
  assigned_to?: string | null;
  internal_note?: string;
  history?: Array<{ from_status: string | null; to_status: string; note: string; created_at: string }>;
};

export type ConsultantProfile = {
  id: string;
  slug: string;
  full_name: string;
  consultant_type: "independent" | "company";
  professional_title: string;
  bio: string;
  specialties: string[];
  years_experience: number;
  rating: number;
  review_count: number;
  consultation_price: number;
  city: string;
  office_address: string;
  is_online: boolean;
  offers_in_person: boolean;
  is_verified: boolean;
  is_available: boolean;
  available_slots?: string[];
};

export type AdvisorStats = {
  conversations: number;
  assistant_messages: number;
  answers_with_citations: number;
  expert_referrals: number;
  helpful_feedback: number;
  not_helpful_feedback: number;
};

export type DocumentItem = {
  id: string;
  title: string;
  document_type: string;
  issuing_authority: string;
  source_url: string | null;
  topics: string[];
  created_at: string;
  version_count: number;
};

export type DocumentVersion = {
  id: string;
  document_id: string;
  version_number: number;
  original_filename: string;
  status: string;
  review_status: string;
  lifecycle_status: string;
  file_size: number;
  chunk_count: number;
  error_code: string | null;
  created_at: string;
};

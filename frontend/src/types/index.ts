export type NavigationPage = 
  | 'dashboard'
  | 'planner'
  | 'advisor'
  | 'transport'
  | 'impact'
  | 'assistant';

export interface BackendHealthResponse {
  status: string;
  app_name: string;
  version: string;
  timestamp_utc: string;
  environment: string;
  gemini_model_configured: string;
}

export type DataState = 
  | 'PROVIDER_REPORTED' 
  | 'CALCULATED' 
  | 'UNAVAILABLE' 
  | 'SIMULATED_DEMO';

export type NAQICategory = 
  | 'Good' 
  | 'Satisfactory' 
  | 'Moderate' 
  | 'Poor' 
  | 'Very Poor' 
  | 'Severe' 
  | 'Unknown';

export interface PollutantMeasurement {
  pollutant: string;
  value: number | null;
  unit: string;
  averaging_hours: number;
  sub_index: number | null;
}

// ==========================================
// Phase 6: Conversational Assistant Types
// ==========================================

export type SupportedLanguage = 'en' | 'hi' | 'hinglish';

export type ChatRole = 'user' | 'assistant';

export type GeminiStatus = 
  | 'AVAILABLE' 
  | 'UNAVAILABLE_NO_KEY' 
  | 'RATE_LIMITED' 
  | 'TIMEOUT' 
  | 'SERVICE_ERROR' 
  | 'SAFETY_BLOCKED' 
  | 'NOT_CALLED';

export interface ChatMessage {
  role: ChatRole;
  content: string;
  timestamp_utc?: string;
}

export interface DeterministicAuthoritativeGuidance {
  applicable_aqi_category: string;
  action_priority: string;
  general_population_advisory: string;
  vulnerable_population_advisory: string;
  schoolchildren_advisory?: string | null;
  essential_travel_guidance?: string | null;
  mask_protective_guidance?: string | null;
  diurnal_timing_note?: string | null;
  source_citation: string;
}

export interface GroundedCitation {
  source_service: string;
  metric_name: string;
  reported_value: string;
  provenance: string;
  freshness: string;
  citation_document: string;
}

export interface AssistantContextInputs {
  station_id?: string | null;
  preferred_language?: SupportedLanguage;
  include_impact_summary?: boolean;
}

export interface AssistantChatRequest {
  message: string;
  conversation_history?: ChatMessage[];
  context_inputs?: AssistantContextInputs;
}

export interface AssistantChatResponse {
  authoritative_guidance?: DeterministicAuthoritativeGuidance | null;
  verified_environmental_facts?: Record<string, any> | null;
  citations: GroundedCitation[];
  gemini_status: GeminiStatus;
  gemini_explanation: string;
  language: SupportedLanguage;
  model_used: string;
  grounding_status: string;
  disclaimer: string;
  privacy_notice: string;
}

export interface AssistantHealthResponse {
  status: 'READY' | 'API_KEY_MISSING';
  configured_model: string;
  api_key_configured: boolean;
  timestamp_utc: string;
}

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

// ==========================================
// Phase 2 & 3: AQI & Station Ingestion Types
// ==========================================

export type ProvenanceType = 
  | 'PROVIDER_REPORTED' 
  | 'CALCULATED' 
  | 'SIMULATED_DEMO' 
  | 'NONE';

export type AvailabilityType = 
  | 'AVAILABLE' 
  | 'UNAVAILABLE';

export type FreshnessType = 
  | 'FRESH' 
  | 'STALE' 
  | 'EXPIRED' 
  | 'DEMO' 
  | 'UNKNOWN';

export type ProviderType = 
  | 'cpcb_datagov' 
  | 'openaq' 
  | 'mock';

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

export interface StationMetadata {
  station_id: string;
  provider: string;
  provider_station_id: string;
  station_name: string;
  city: string;
  state: string;
  latitude?: number | null;
  longitude?: number | null;
  country: string;
  timezone: string;
}

export interface StationPollutantMeasurement {
  pollutant: string;
  sensor_id?: string | null;
  value: number;
  unit: string;
  observed_at_utc: string;
  averaging_period_hours: number;
  coverage_hours?: number | null;
  provider: string;
  source: string;
  freshness: FreshnessType;
}

export interface StationAQIResponse {
  station: StationMetadata;
  provenance: ProvenanceType;
  availability: AvailabilityType;
  freshness: FreshnessType;
  provider_reported_aqi?: number | null;
  provider_reported_category?: string | null;
  calculated_aqi?: number | null;
  overall_aqi?: number | null;
  overall_aqi_lower_bound?: number | null;
  overall_aqi_upper_bound?: number | null;
  is_exact: boolean;
  category: string;
  dominant_pollutant?: string | null;
  pollutant_measurements: Record<string, StationPollutantMeasurement>;
  source: string;
  observed_at_utc?: string | null;
  observed_at_ist?: string | null;
  fetched_at_utc: string;
  warnings: string[];
  unavailable_reason?: string | null;
}

export interface StationListResponse {
  total: number;
  stations: StationMetadata[];
  provider: string;
  demo_mode: boolean;
  warnings: string[];
}

export interface PollutantMeasurement {
  pollutant: string;
  value: number;
  unit: string;
  averaging_hours?: number;
  hours_recorded?: number;
  recorded_at?: string | null;
  sub_index?: number | null;
}

export interface PollutantSubIndex {
  pollutant: string;
  concentration: number;
  unit: string;
  averaging_hours: number;
  hours_recorded: number;
  sub_index?: number | null;
  sub_index_lower_bound?: number | null;
  sub_index_upper_bound?: number | null;
  is_exact: boolean;
  category: string;
  is_valid: boolean;
  validation_error?: string | null;
  note?: string | null;
}

export interface OverallAQIResult {
  overall_aqi?: number | null;
  overall_aqi_lower_bound?: number | null;
  overall_aqi_upper_bound?: number | null;
  is_exact: boolean;
  category: string;
  dominant_pollutant?: string | null;
  status: string;
  reason: string;
  eligible_for_overall_aqi: boolean;
  valid_pollutants_count: number;
  has_mandatory_pm: boolean;
  sub_indices: Record<string, PollutantSubIndex>;
  timestamp_utc: string;
}

export interface AQICalculationRequest {
  measurements: PollutantMeasurement[];
}

// ==========================================
// Phase 4: Daily Planner Types
// ==========================================

export type HouseholdBudget = 'low' | 'medium' | 'high';

export type CommuteMethod =
  | 'walk'
  | 'bicycle'
  | 'two_wheeler'
  | 'auto_rickshaw'
  | 'bus'
  | 'metro'
  | 'car_non_ac'
  | 'car_ac'
  | 'carpool'
  | 'work_from_home';

export type ActivityType =
  | 'school_commute'
  | 'work_commute'
  | 'outdoor_exercise'
  | 'outdoor_play'
  | 'outdoor_sports'
  | 'shopping_errands'
  | 'essential_travel'
  | 'essential_medical_travel'
  | 'indoor_activities';

export type ActivityIntensity = 'low' | 'moderate' | 'high';
export type ActivityNecessity = 'essential' | 'discretionary' | 'optional';
export type ActionPriority = 'LOW' | 'MODERATE' | 'HIGH' | 'URGENT';

export interface ActivityPlanItem {
  activity_type: ActivityType;
  intensity?: ActivityIntensity;
  necessity?: ActivityNecessity;
  scheduled_time?: string | null;
  notes?: string | null;
}

export interface DailyPlannerRequest {
  station_id: string;
  family_size?: number;
  has_children?: boolean;
  has_older_adults?: boolean;
  has_sensitive_member?: boolean;
  household_budget?: HouseholdBudget;
  commute_method?: CommuteMethod;
  school_schedule?: string | null;
  work_schedule?: string | null;
  planned_activities?: ActivityPlanItem[];
  activity_intensity?: ActivityIntensity;
  activity_necessity?: ActivityNecessity;
  preferred_language?: string;
}

export interface PlannerAQIContext {
  overall_aqi?: number | null;
  overall_aqi_lower_bound?: number | null;
  overall_aqi_upper_bound?: number | null;
  is_exact: boolean;
  category: string;
  dominant_pollutant?: string | null;
  provenance: string;
  availability: string;
  freshness: string;
  observed_at_ist?: string | null;
}

export interface PlannerRecommendationItem {
  activity_type: string;
  action: string;
  recommendation: string;
  reason: string;
  alternative_activity: string;
  target_group: string;
  practical_steps: string[];
}

export interface StructuredAdvisoryReference {
  issuing_organization: string;
  document_title: string;
  publication_year: string;
  applicable_aqi_category: string;
  relevant_section: string;
  public_source_url: string;
}

export interface DailyPlannerResponse {
  generated_at: string;
  station_id: string;
  station_name: string;
  city: string;
  aqi_context: PlannerAQIContext;
  action_priority: ActionPriority;
  public_health_summary: string;
  general_population_advisory: string;
  vulnerable_population_advisory: string;
  conditional_timing_guidance?: Record<string, string> | null;
  recommendations: PlannerRecommendationItem[];
  general_household_practices: string[];
  structured_advisory_reference: StructuredAdvisoryReference;
  evidence_source: string;
  data_limitations: string[];
  warnings: string[];
}

// ==========================================
// Phase 4: Indoor Air Quality Advisor Types
// ==========================================

export type CADRUnit = 'm3/h' | 'CFM';

export interface RoomDimensions {
  length_m: number;
  width_m: number;
  height_m: number;
}

export interface IndoorAssessmentRequest {
  station_id?: string | null;
  room_length_m: number;
  room_width_m: number;
  ceiling_height_m: number;
  has_air_purifier?: boolean;
  cadr?: number | null;
  smoke_cadr?: number | null;
  cadr_unit?: CADRUnit;
  filter_type?: string | null;
  indoor_pollution_sources?: string[];
  ventilation_available?: boolean;
  household_budget?: HouseholdBudget;
  target_ach?: number | null;
}

export interface FiltrationAssessment {
  purifier_status: string;
  target_comparison?: string | null;
  is_user_reported_filter: boolean;
  explanation: string;
  guidance: string[];
}

export interface IndoorActionItem {
  source: string;
  action: string;
  priority: string;
  reason: string;
}

export interface VentilationAdvisory {
  outdoor_aqi_category?: string | null;
  strategy: string;
  guidance: string;
  precautions: string[];
}

export interface IndoorAssessmentResponse {
  generated_at: string;
  room_dimensions: RoomDimensions;
  room_volume_m3: number;
  available_cadr_m3h?: number | null;
  available_cadr_cfm?: number | null;
  calculated_ach?: number | null;
  target_ach?: number | null;
  required_cadr_m3h?: number | null;
  required_cadr_cfm?: number | null;
  filtration_assessment: FiltrationAssessment;
  source_control_recommendations: IndoorActionItem[];
  ventilation_recommendations: VentilationAdvisory;
  affordable_interventions: string[];
  formula_and_assumptions: Record<string, string>;
  data_source_and_limitations: string[];
  warnings: string[];
}

// ==========================================
// Phase 5: Transport Advisor Types
// ==========================================

export type TransportMode =
  | 'petrol_motorcycle'
  | 'petrol_car'
  | 'diesel_car'
  | 'cng_auto'
  | 'intracity_bus'
  | 'metro'
  | 'carpool'
  | 'electric_vehicle'
  | 'walking'
  | 'cycling';

export type FuelType = 'petrol' | 'diesel' | 'cng' | 'electric' | 'none';

export type FactorVerificationStatus = 'VERIFIED_CURRENT' | 'HISTORICAL_PROVISIONAL' | 'UNAVAILABLE';

export interface EmissionFactorEntry {
  factor_id: string;
  mode: string;
  fuel_type?: string | null;
  engine_capacity_boundary?: string | null;
  base_value?: number | null;
  uplift_pct?: number | null;
  default_value: number;
  unit: string;
  is_default_for_calc: boolean;
  verification_status: FactorVerificationStatus;
  source_name: string;
  document_title: string;
  publication_year: number;
  publication_date?: string | null;
  applicable_fiscal_year?: string | null;
  source_page?: string | null;
  geography: string;
  calculation_scope: string;
  limitations: string;
  methodology_notes?: string | null;
}

export interface EmissionFactorRegistryResponse {
  total_factors: number;
  retrieved_at_utc: string;
  factors: EmissionFactorEntry[];
  registry_notes: string[];
}

export interface TransportModeResult {
  mode: TransportMode;
  is_available: boolean;
  unavailable_reason?: string | null;
  factor_id_used?: string | null;
  factor_value?: number | null;
  factor_unit?: string | null;
  factor_status?: FactorVerificationStatus | null;
  effective_distance_km: number;
  occupancy: number;
  total_vehicle_emissions_kg_co2?: number | null;
  passenger_emissions_kg_co2?: number | null;
  is_user_guided: boolean;
  user_guided_source_note?: string | null;
  health_guidance_note?: string | null;
  is_recommended_for_commute: boolean;
  lifecycle_disclosure?: string | null;
  calculation_trace: string[];
}

export interface AvoidedEmissionsComparison {
  alternative_mode: TransportMode;
  baseline_passenger_emissions_kg_co2: number;
  alternative_passenger_emissions_kg_co2?: number | null;
  avoided_kg_co2_per_trip?: number | null;
  is_emissions_increase: boolean;
  projected_weekly_saving_kg_co2?: number | null;
  projected_monthly_saving_kg_co2?: number | null;
  comparison_summary: string;
}

export interface TransportComparisonRequest {
  station_id: string;
  current_mode: TransportMode;
  fuel_type?: FuelType | null;
  engine_capacity_cc?: number | null;
  distance_km: number;
  round_trip?: boolean;
  occupancy?: number;
  trips_per_week?: number;
  alternatives: TransportMode[];
  user_cost_current_inr?: number | null;
  household_budget?: HouseholdBudget;
  has_children?: boolean;
  has_older_adults?: boolean;
  has_sensitive_member?: boolean;
  user_ev_kwh_per_km?: number | null;
  user_metro_kwh_per_pax_km?: number | null;
}

export interface TransportComparisonResponse {
  generated_at_utc: string;
  station_id: string;
  station_name: string;
  city: string;
  current_aqi?: number | null;
  aqi_category: string;
  ncdc_general_advisory: string;
  ncdc_vulnerable_advisory: string;
  effective_distance_km: number;
  round_trip: boolean;
  baseline_result: TransportModeResult;
  alternative_results: TransportModeResult[];
  avoided_comparisons: AvoidedEmissionsComparison[];
  disclaimers: string[];
  limitations: string[];
}

// ==========================================
// Phase 5: Impact Tracker Types
// ==========================================

export interface BaselineTripInput {
  mode: TransportMode;
  fuel_type?: FuelType | null;
  engine_capacity_cc?: number | null;
  occupancy?: number;
  user_ev_kwh_per_km?: number | null;
  user_metro_kwh_per_pax_km?: number | null;
}

export interface TripLogEntry {
  mode: TransportMode;
  fuel_type?: FuelType | null;
  engine_capacity_cc?: number | null;
  distance_km: number;
  round_trip?: boolean;
  occupancy?: number;
  baseline_scenario?: BaselineTripInput | null;
  user_ev_kwh_per_km?: number | null;
  user_metro_kwh_per_pax_km?: number | null;
  station_id?: string | null;
  user_reported_aqi_category?: string | null;
  notes?: string | null;
}

export interface CompletedTripRecord {
  trip_id: string;
  idempotency_key: string;
  logged_at_utc: string;
  mode: TransportMode;
  effective_distance_km: number;
  round_trip: boolean;
  occupancy: number;
  passenger_emissions_kg_co2: number;
  factor_id_used: string;
  factor_status: string;
  baseline_mode?: TransportMode | null;
  baseline_passenger_emissions_kg_co2?: number | null;
  actual_avoided_kg_co2?: number | null;
  avoided_status: string;
  avoided_explanation: string;
  aqi_context_source: string;
  aqi_category?: string | null;
  notes?: string | null;
}

export interface SessionCreationResponse {
  session_id: string;
  created_at_utc: string;
  expires_at_utc: string;
  storage_disclaimer: string;
}

export interface TripLogResult {
  session_id: string;
  trip: CompletedTripRecord;
  storage_disclaimer: string;
  message: string;
}

export interface WeeklyActualSummary {
  iso_year: number;
  iso_week: number;
  trip_count: number;
  total_passenger_emissions_kg_co2: number;
  total_avoided_kg_co2: number;
  emissions_increase_trips: number;
}

export interface MonthlyActualSummary {
  year: number;
  month: number;
  trip_count: number;
  total_passenger_emissions_kg_co2: number;
  total_avoided_kg_co2: number;
  emissions_increase_trips: number;
}

export interface ImpactSessionSummary {
  session_id: string;
  created_at_utc: string;
  last_accessed_at_utc: string;
  expires_at_utc: string;
  storage_disclaimer: string;
  completed_action_count: number;
  actual_total_emissions_kg_co2: number;
  actual_avoided_kg_co2: number;
  trips_without_baseline_count: number;
  emissions_by_mode: Record<string, number>;
  weekly_summaries: WeeklyActualSummary[];
  monthly_summaries: MonthlyActualSummary[];
  completed_trips: CompletedTripRecord[];
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

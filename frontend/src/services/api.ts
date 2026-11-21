import type {
  BackendHealthResponse,
  // AQI & Stations
  StationListResponse,
  StationAQIResponse,
  AQICalculationRequest,
  OverallAQIResult,
  // Planner
  DailyPlannerRequest,
  DailyPlannerResponse,
  // Indoor Advisor
  IndoorAssessmentRequest,
  IndoorAssessmentResponse,
  // Transport Advisor
  EmissionFactorRegistryResponse,
  TransportComparisonRequest,
  TransportComparisonResponse,
  // Impact Tracker
  SessionCreationResponse,
  TripLogEntry,
  TripLogResult,
  ImpactSessionSummary,
  // Assistant
  AssistantChatRequest,
  AssistantChatResponse,
  AssistantHealthResponse,
} from '../types';

export const API_BASE_URL = 
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || 
  'https://smogshieldai.onrender.com/api/v1';

/**
 * Universal error parser for FastAPI standard responses (including 422 Unprocessable Entity,
 * 429 Rate Limits, 404 Not Found, and 500 Internal Errors).
 */
async function handleResponseError(response: Response): Promise<never> {
  let errorDetail = `Request failed with status ${response.status} (${response.statusText})`;

  try {
    const errorJson = await response.json();
    if (errorJson) {
      if (typeof errorJson.detail === 'string') {
        errorDetail = errorJson.detail;
      } else if (Array.isArray(errorJson.detail)) {
        // Pydantic validation error array: [{loc: [...], msg: "...", type: "..."}]
        const messages = errorJson.detail.map((err: { loc?: string[]; msg?: string }) => {
          const field = err.loc ? err.loc.filter(l => l !== 'body').join('.') : 'field';
          return `${field ? field + ': ' : ''}${err.msg || 'Invalid value'}`;
        });
        errorDetail = `Validation failed: ${messages.join('; ')}`;
      } else if (errorJson.message) {
        errorDetail = String(errorJson.message);
      }
    }
  } catch {
    errorDetail = `${response.status} ${response.statusText}`;
  }

  if (response.status === 429) {
    const retryAfter = response.headers.get('Retry-After');
    const waitMsg = retryAfter ? ` Please wait ${retryAfter} seconds before trying again.` : '';
    throw new Error(`Rate limit exceeded: ${errorDetail}${waitMsg}`);
  }

  throw new Error(errorDetail);
}

/**
 * Common typed fetch utility with abort timeout and error handling.
 */
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  timeoutMs: number = 30000
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });

    if (!response.ok) {
      await handleResponseError(response);
    }

    return (await response.json()) as T;
  } catch (error: unknown) {
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new Error(`Request timeout: The server took longer than ${timeoutMs / 1000}s to respond.`);
      }
      throw error;
    }
    throw new Error('An unexpected network or client error occurred.');
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Root health check endpoint (/health on API router).
 */
export async function fetchHealthCheck(): Promise<BackendHealthResponse> {
  return apiFetch<BackendHealthResponse>('/health');
}

// ==========================================
// Phase 2 & 3: AQI & Station Ingestion Service
// ==========================================

export const aqiApi = {
  /**
   * Discover monitoring stations with verified metadata from configured providers.
   * Supports city-based search and provider filtering.
   */
  async listStations(params?: { city?: string; provider?: string }): Promise<StationListResponse> {
    const query = new URLSearchParams();
    if (params?.city) query.append('city', params.city);
    if (params?.provider) query.append('provider', params.provider);
    const queryString = query.toString() ? `?${query.toString()}` : '';

    return apiFetch<StationListResponse>(`/aqi/stations${queryString}`);
  },

  /**
   * Retrieve the latest air quality report for a specific monitoring station.
   */
  async getStationAqi(stationId: string): Promise<StationAQIResponse> {
    return apiFetch<StationAQIResponse>(`/aqi/station/${encodeURIComponent(stationId)}`);
  },

  /**
   * Calculate CPCB National AQI, individual sub-indices, and category classification
   * using official CPCB 2014 linear segmentation formula.
   */
  async calculateAqi(request: AQICalculationRequest): Promise<OverallAQIResult> {
    return apiFetch<OverallAQIResult>('/aqi/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
  },
};

// ==========================================
// Phase 4: Daily Planner Service
// ==========================================

export const plannerApi = {
  /**
   * Generate deterministic personalized daily planner recommendations.
   * Evaluates household family profile, planned activities, and commute method against
   * verified ambient air quality from the selected monitoring station.
   */
  async generate(request: DailyPlannerRequest): Promise<DailyPlannerResponse> {
    return apiFetch<DailyPlannerResponse>('/planner/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
  },
};

// ==========================================
// Phase 4: Indoor Air Quality Advisor Service
// ==========================================

export const advisorApi = {
  /**
   * Generate deterministic indoor air assessment and purifier sizing.
   * Computes geometrical room volume, evaluates CADR and ACH, and provides
   * condition-based ventilation advice.
   */
  async assessIndoor(request: IndoorAssessmentRequest): Promise<IndoorAssessmentResponse> {
    return apiFetch<IndoorAssessmentResponse>('/advisor/indoor-assessment', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
  },
};

// ==========================================
// Phase 5: Transportation Advisor Service
// ==========================================

export const transportApi = {
  /**
   * Read audited emission factor registry (9 audited factors).
   */
  async getEmissionFactors(params?: { mode?: string; fuel_type?: string }): Promise<EmissionFactorRegistryResponse> {
    const query = new URLSearchParams();
    if (params?.mode) query.append('mode', params.mode);
    if (params?.fuel_type) query.append('fuel_type', params.fuel_type);
    const queryString = query.toString() ? `?${query.toString()}` : '';

    return apiFetch<EmissionFactorRegistryResponse>(`/transport/emission-factors${queryString}`);
  },

  /**
   * Compare transport modes with AQI integration and health advisory evaluation.
   */
  async compare(request: TransportComparisonRequest): Promise<TransportComparisonResponse> {
    return apiFetch<TransportComparisonResponse>('/transport/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
  },
};

// ==========================================
// Phase 5: Environmental Impact Tracker Service
// ==========================================

function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'req_' + Date.now() + '_' + Math.random().toString(36).substring(2, 11);
}

export const impactApi = {
  /**
   * Create a new isolated in-memory impact tracking session.
   * Issues a server-generated UUID4 session bearer token valid for 24 hours of inactivity.
   */
  async createSession(): Promise<SessionCreationResponse> {
    return apiFetch<SessionCreationResponse>('/impact/sessions', {
      method: 'POST',
    });
  },

  /**
   * Log a completed sustainable or commute trip against an active session.
   * Calculates 100% of emissions server-side with idempotency protection.
   * Requires X-Session-ID and Idempotency-Key headers.
   */
  async logTrip(
    entry: TripLogEntry,
    sessionId: string,
    idempotencyKey?: string
  ): Promise<TripLogResult> {
    if (!sessionId) {
      throw new Error('A valid session ID is required to log a trip.');
    }

    const key = idempotencyKey || generateUUID();

    return apiFetch<TripLogResult>('/impact/log-trip', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId,
        'Idempotency-Key': key,
      },
      body: JSON.stringify(entry),
    });
  },

  /**
   * Get comprehensive impact summary for an active session.
   * Requires X-Session-ID header.
   */
  async getSessionSummary(sessionId: string): Promise<ImpactSessionSummary> {
    if (!sessionId) {
      throw new Error('A valid session ID is required to fetch session summary.');
    }

    return apiFetch<ImpactSessionSummary>('/impact/session-summary', {
      method: 'GET',
      headers: {
        'X-Session-ID': sessionId,
      },
    });
  },
};

// ==========================================
// Phase 6: Conversational AI Assistant Service
// ==========================================

export const assistantApi = {
  /**
   * Consult the SmogShield AI Conversational Assistant.
   * Sends user prompt, recent bounded conversation turns, and verified context parameters.
   * When impact summary is explicitly requested and a valid session is active,
   * passes X-Session-ID header (never in JSON body).
   */
  async chat(
    request: AssistantChatRequest,
    sessionId?: string
  ): Promise<AssistantChatResponse> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (sessionId && request.context_inputs?.include_impact_summary) {
      headers['X-Session-ID'] = sessionId;
    }

    return apiFetch<AssistantChatResponse>('/assistant/chat', {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
    });
  },

  /**
   * Passive readiness check for the assistant generative layer.
   * Never invokes Gemini API; consumes zero tokens.
   */
  async getHealth(): Promise<AssistantHealthResponse> {
    return apiFetch<AssistantHealthResponse>('/assistant/health');
  },
};

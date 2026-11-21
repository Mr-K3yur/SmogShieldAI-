import { 
  BackendHealthResponse, 
  AssistantChatRequest, 
  AssistantChatResponse,
  AssistantHealthResponse 
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export async function fetchHealthCheck(): Promise<BackendHealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Backend health check failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

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

    const response = await fetch(`${API_BASE_URL}/assistant/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      let errorDetail = `Request failed (${response.status})`;
      try {
        const errorJson = await response.json();
        if (errorJson && typeof errorJson.detail === 'string') {
          errorDetail = errorJson.detail;
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

    return response.json();
  },

  /**
   * Passive readiness check for the assistant generative layer.
   * Never invokes Gemini API; consumes zero tokens.
   */
  async getHealth(): Promise<AssistantHealthResponse> {
    const response = await fetch(`${API_BASE_URL}/assistant/health`);
    if (!response.ok) {
      throw new Error(`Assistant health check failed: ${response.status} ${response.statusText}`);
    }
    return response.json();
  },
};

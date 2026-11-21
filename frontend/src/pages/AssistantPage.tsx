import React, { useState, useEffect } from 'react';
import { AlertCircle } from 'lucide-react';
import { 
  BackendHealthResponse, 
  SupportedLanguage, 
  ChatMessage, 
  DeterministicAuthoritativeGuidance, 
  AssistantHealthResponse,
  AssistantChatRequest,
  AssistantChatResponse
} from '../types';
import { assistantApi } from '../services/api';
import { AssistantHeader } from '../components/assistant/AssistantHeader';
import { AuthoritativeGuidanceCard } from '../components/assistant/AuthoritativeGuidanceCard';
import { ChatMessageList } from '../components/assistant/ChatMessageList';
import { MessageComposer } from '../components/assistant/MessageComposer';
import { QuickSuggestions } from '../components/assistant/QuickSuggestions';
import { DisplayMessage } from '../components/assistant/ChatMessageBubble';

interface AssistantPageProps {
  health: BackendHealthResponse | null;
}

export const AssistantPage: React.FC<AssistantPageProps> = ({ health }) => {
  // In-memory conversation state (strictly never persisted to localStorage or sessionStorage)
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [authoritativeGuidance, setAuthoritativeGuidance] = useState<DeterministicAuthoritativeGuidance | null>(null);
  const [language, setLanguage] = useState<SupportedLanguage>('en');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [assistantHealth, setAssistantHealth] = useState<AssistantHealthResponse | null>(null);

  // Passive health check for the assistant on mount
  useEffect(() => {
    let isMounted = true;
    async function loadHealth() {
      try {
        const h = await assistantApi.getHealth();
        if (isMounted) {
          setAssistantHealth(h);
        }
      } catch {
        // Fallback to parent health prop or default if health check endpoint fails
        if (isMounted && health) {
          setAssistantHealth({
            status: 'READY',
            configured_model: health.gemini_model_configured || 'gemini-3.8-flash',
            api_key_configured: true,
            timestamp_utc: new Date().toISOString(),
          });
        }
      }
    }
    loadHealth();
    return () => {
      isMounted = false;
    };
  }, [health]);

  // Handle sending a user message
  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    setErrorMessage(null);

    // 1. Create client message item with unique ID
    const userMessageId = `user-${Date.now()}`;
    const userMessage: DisplayMessage = {
      id: userMessageId,
      role: 'user',
      content: text,
      timestamp_utc: new Date().toISOString(),
    };

    // 2. Prepare bounded conversation history for backend (max 6 messages / recent 3 turns)
    // CRITICAL: We pass prior conversation history, NOT including the current message
    const previousHistory: ChatMessage[] = messages
      .slice(-6)
      .map((m) => ({
        role: m.role,
        content: m.content,
        timestamp_utc: m.timestamp_utc,
      }));

    // Update optimistic UI state with user message
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // 3. Assemble AssistantChatRequest
      const requestPayload: AssistantChatRequest = {
        message: text,
        conversation_history: previousHistory,
        context_inputs: {
          preferred_language: language,
          // Optional station ID could be linked if user navigated from Dashboard
          station_id: 'stn_delhi_ito',
        },
      };

      // 4. Invoke backend API: POST /api/v1/assistant/chat
      const response: AssistantChatResponse = await assistantApi.chat(requestPayload);

      // 5. Update Authoritative Guidance separately (NEVER populated from Gemini text)
      if (response.authoritative_guidance) {
        setAuthoritativeGuidance(response.authoritative_guidance);
      }

      // 6. Append assistant message with status, citations, model metadata
      const assistantMessageId = `assistant-${Date.now()}`;
      const assistantMessage: DisplayMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: response.gemini_explanation,
        timestamp_utc: new Date().toISOString(),
        gemini_status: response.gemini_status,
        model_used: response.model_used,
        citations: response.citations,
        disclaimer: response.disclaimer,
        grounding_status: response.grounding_status,
        isFallback: response.gemini_status !== 'AVAILABLE',
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errText = err instanceof Error ? err.message : 'Failed to reach SmogShield assistant service.';
      setErrorMessage(errText);
    } finally {
      setIsLoading(false);
    }
  };

  // Reset conversation in-memory state
  const handleResetConversation = () => {
    setMessages([]);
    setErrorMessage(null);
  };

  return (
    <div className="space-y-5 max-w-5xl mx-auto">
      {/* 1. Header with Language Selector & Health Status */}
      <AssistantHeader
        language={language}
        onLanguageChange={setLanguage}
        onResetConversation={handleResetConversation}
        assistantHealth={assistantHealth}
        messageCount={messages.length}
      />

      {/* 2. Deterministic Action Guidance Card (Independent from Gemini prose) */}
      <section aria-labelledby="authoritative-guidance-heading">
        <h2 id="authoritative-guidance-heading" className="sr-only">
          Authoritative Public Health Guidance
        </h2>
        <AuthoritativeGuidanceCard guidance={authoritativeGuidance} />
      </section>

      {/* Error Banner (if network or API failure) */}
      {errorMessage && (
        <div
          role="alert"
          className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs sm:text-sm flex items-start gap-2.5 shadow-sm"
        >
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold">Assistant Connection Notice:</span>
            <p>{errorMessage}</p>
          </div>
        </div>
      )}

      {/* 3. Conversation Area */}
      <section aria-labelledby="chat-messages-heading" className="bg-slate-50/50 rounded-2xl p-2 sm:p-4">
        <h2 id="chat-messages-heading" className="sr-only">
          Conversation Messages
        </h2>
        <ChatMessageList
          messages={messages}
          isLoading={isLoading}
          language={language}
          onSelectSuggestion={handleSendMessage}
        />
      </section>

      {/* Quick Suggestions (rendered above composer when messages exist) */}
      {messages.length > 0 && (
        <QuickSuggestions
          language={language}
          onSelectSuggestion={handleSendMessage}
          disabled={isLoading}
        />
      )}

      {/* 4. Message Composer & Privacy Disclosure */}
      <section aria-label="Message Input">
        <MessageComposer
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          language={language}
        />
      </section>
    </div>
  );
};

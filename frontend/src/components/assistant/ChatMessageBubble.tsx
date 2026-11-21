import React from 'react';
import { Bot, User, Sparkles, Shield, AlertTriangle } from 'lucide-react';
import { ChatMessage, GeminiStatus, GroundedCitation } from '../../types';
import { GroundedCitations } from './GroundedCitations';

export interface DisplayMessage extends ChatMessage {
  id: string;
  gemini_status?: GeminiStatus;
  model_used?: string;
  citations?: GroundedCitation[];
  disclaimer?: string;
  grounding_status?: string;
  isFallback?: boolean;
}

interface ChatMessageBubbleProps {
  message: DisplayMessage;
}

export const ChatMessageBubble: React.FC<ChatMessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  // Format simple text paragraphs safely without dangerouslySetInnerHTML
  const renderFormattedContent = (content: string) => {
    return content.split('\n\n').map((paragraph, pIdx) => {
      // Split lines within paragraph
      const lines = paragraph.split('\n');
      return (
        <p key={pIdx} className="mb-2 last:mb-0 leading-relaxed text-sm">
          {lines.map((line, lIdx) => (
            <React.Fragment key={lIdx}>
              {line}
              {lIdx < lines.length - 1 && <br />}
            </React.Fragment>
          ))}
        </p>
      );
    });
  };

  const renderStatusBadge = (status?: GeminiStatus, model?: string) => {
    if (!status) return null;

    switch (status) {
      case 'AVAILABLE':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <Sparkles className="w-3 h-3 text-emerald-600" />
            <span>AI Explanation ({model || 'gemini-3.8-flash'})</span>
          </span>
        );
      case 'UNAVAILABLE_NO_KEY':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <Shield className="w-3 h-3 text-blue-600" />
            <span>Official NCDC Advisory (Deterministic Mode)</span>
          </span>
        );
      case 'RATE_LIMITED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            <span>Deterministic Advisory (Quota Exhausted)</span>
          </span>
        );
      case 'TIMEOUT':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            <span>Deterministic Advisory (Timeout Fallback)</span>
          </span>
        );
      case 'SAFETY_BLOCKED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <Shield className="w-3 h-3 text-rose-600" />
            <span>Deterministic Advisory (Safety Policy Fallback)</span>
          </span>
        );
      case 'SERVICE_ERROR':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            <Shield className="w-3 h-3 text-slate-500" />
            <span>Deterministic Health Advisory</span>
          </span>
        );
    }
  };

  if (isUser) {
    return (
      <div className="flex justify-end gap-2.5 my-3">
        <div className="max-w-[85%] sm:max-w-[75%] bg-slate-900 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
          <div className="text-sm leading-relaxed">{renderFormattedContent(message.content)}</div>
          {message.timestamp_utc && (
            <div className="text-[10px] text-slate-400 text-right mt-1 font-mono">
              {new Date(message.timestamp_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
          )}
        </div>
        <div className="w-7 h-7 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center flex-shrink-0 mt-1">
          <User className="w-4 h-4" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start gap-2.5 my-4">
      <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center flex-shrink-0 mt-1 shadow-sm">
        <Bot className="w-4 h-4" />
      </div>

      <div className="max-w-[90%] sm:max-w-[80%] bg-white rounded-2xl rounded-tl-sm border border-slate-200 p-4 sm:p-5 shadow-sm space-y-2">
        {/* Assistant Header: Model / Status Badge */}
        <div className="flex items-center justify-between gap-2 pb-2 border-b border-slate-100 flex-wrap">
          <span className="text-xs font-semibold text-slate-800">SmogShield Assistant</span>
          {renderStatusBadge(message.gemini_status, message.model_used)}
        </div>

        {/* Message Prose */}
        <div className="text-slate-800 text-sm">{renderFormattedContent(message.content)}</div>

        {/* Grounded Citations (if present) */}
        {message.citations && message.citations.length > 0 && (
          <GroundedCitations citations={message.citations} />
        )}

        {/* Disclaimer / Timestamp Footer */}
        <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px] text-slate-400">
          <span>{message.disclaimer || 'Official CPCB/NCDC public health guidelines. Non-clinical.'}</span>
          {message.timestamp_utc && (
            <span className="font-mono">
              {new Date(message.timestamp_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

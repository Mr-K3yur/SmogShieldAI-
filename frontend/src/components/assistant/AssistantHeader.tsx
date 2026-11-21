import React from 'react';
import { Bot, RotateCcw, ShieldCheck, AlertTriangle } from 'lucide-react';
import { SupportedLanguage, AssistantHealthResponse } from '../../types';

interface AssistantHeaderProps {
  language: SupportedLanguage;
  onLanguageChange: (lang: SupportedLanguage) => void;
  onResetConversation: () => void;
  assistantHealth: AssistantHealthResponse | null;
  messageCount: number;
}

export const AssistantHeader: React.FC<AssistantHeaderProps> = ({
  language,
  onLanguageChange,
  onResetConversation,
  assistantHealth,
  messageCount,
}) => {
  const isReady = assistantHealth?.status === 'READY';
  const configuredModel = assistantHealth?.configured_model || 'gemini-3.8-flash';

  const languageLabels: Record<SupportedLanguage, { label: string; sub: string }> = {
    en: { label: 'English', sub: 'Standard' },
    hi: { label: 'हिंदी', sub: 'Devanagari' },
    hinglish: { label: 'Hinglish', sub: 'Conversational' },
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 sm:p-6 transition-all">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Title and Branding */}
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <Bot className="w-3.5 h-3.5" />
            SmogShield AI Assistant
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Family Air Defense & Smog Navigator
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 max-w-2xl">
            {language === 'hi'
              ? 'भारतीय परिवारों के लिए आधिकारिक CPCB और NCDC स्वास्थ्य दिशानिर्देशों पर आधारित व्याख्यात्मक सलाह।'
              : language === 'hinglish'
              ? 'Indian families ke liye verified CPCB aur NCDC guidelines par based helpful conversational guidance.'
              : 'Contextual public health advisories and commute guidance grounded in official CPCB and NCDC standards.'}
          </p>
        </div>

        {/* Controls: Language Selector, Status & Reset */}
        <div className="flex flex-wrap items-center gap-2.5 sm:gap-3">
          {/* Status Badge */}
          <div
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border ${
              isReady
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-amber-50 text-amber-700 border-amber-200'
            }`}
            title={`Backend Gemini Model: ${configuredModel}`}
          >
            {isReady ? (
              <>
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                <span>{configuredModel}</span>
              </>
            ) : (
              <>
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                <span>Deterministic Mode</span>
              </>
            )}
          </div>

          {/* Language Selector */}
          <div className="inline-flex bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs">
            {(['en', 'hi', 'hinglish'] as SupportedLanguage[]).map((lang) => {
              const active = language === lang;
              return (
                <button
                  key={lang}
                  type="button"
                  onClick={() => onLanguageChange(lang)}
                  className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                    active
                      ? 'bg-white text-slate-900 shadow-sm font-semibold'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                  aria-pressed={active}
                  aria-label={`Select ${languageLabels[lang].label} language`}
                >
                  {languageLabels[lang].label}
                </button>
              );
            })}
          </div>

          {/* Reset / New Conversation Button */}
          {messageCount > 0 && (
            <button
              type="button"
              onClick={onResetConversation}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 hover:border-slate-300 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
              title="Clear conversation history and start fresh"
              aria-label="Start new conversation"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
              <span>New Chat</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

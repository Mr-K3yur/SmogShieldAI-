import React, { useEffect, useRef } from 'react';
import { Bot, Loader2, Sparkles, Shield, HeartHandshake } from 'lucide-react';
import { DisplayMessage, ChatMessageBubble } from './ChatMessageBubble';
import { QuickSuggestions } from './QuickSuggestions';
import { SupportedLanguage } from '../../types';

interface ChatMessageListProps {
  messages: DisplayMessage[];
  isLoading: boolean;
  language: SupportedLanguage;
  onSelectSuggestion: (question: string) => void;
}

export const ChatMessageList: React.FC<ChatMessageListProps> = ({
  messages,
  isLoading,
  language,
  onSelectSuggestion,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  if (messages.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8 shadow-sm text-center my-4 space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-emerald-50 text-emerald-600 mx-auto flex items-center justify-center shadow-inner">
          <Bot className="w-8 h-8" />
        </div>

        <div className="space-y-2 max-w-lg mx-auto">
          <h2 className="text-lg font-bold text-slate-900">
            {language === 'hi'
              ? 'स्मॉगशील्ड एआई असिस्टेंट में आपका स्वागत है'
              : language === 'hinglish'
              ? 'Welcome to SmogShield AI Assistant'
              : 'Welcome to SmogShield AI Assistant'}
          </h2>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {language === 'hi'
              ? 'मैं भारतीय परिवारों और यात्रियों को आधिकारिक सीपीसीबी वायु गुणवत्ता और एनसीडीसी स्वास्थ्य दिशानिर्देशों को समझने में मदद करता हूं।'
              : language === 'hinglish'
              ? 'Main Indian families aur commuters ko verified CPCB AQI aur NCDC health guidelines explain karne mein help karta hu.'
              : 'I help Indian families, parents, schoolchildren, and commuters understand real-time CPCB air quality readings and official NCDC 2025 public health advisories.'}
          </p>
        </div>

        {/* Feature Highlights */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-left max-w-2xl mx-auto pt-2">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800">
              <Shield className="w-3.5 h-3.5 text-emerald-600" />
              <span>Grounded Facts</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Zero hallucinated metrics. All AQI and CO₂ numbers are computed server-side.
            </p>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800">
              <HeartHandshake className="w-3.5 h-3.5 text-rose-600" />
              <span>Family Safety</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Tailored guidance for schoolchildren, asthmatics, elderly, and daily commuters.
            </p>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800">
              <Sparkles className="w-3.5 h-3.5 text-blue-600" />
              <span>Bilingual Ease</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Natural conversations in English, Hindi (हिंदी), or conversational Hinglish.
            </p>
          </div>
        </div>

        {/* Quick Suggestions on Welcome */}
        <div className="pt-2 max-w-2xl mx-auto text-left">
          <QuickSuggestions
            language={language}
            onSelectSuggestion={onSelectSuggestion}
            disabled={isLoading}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3 min-h-[350px] max-h-[600px] overflow-y-auto pr-1">
      {messages.map((msg) => (
        <ChatMessageBubble key={msg.id} message={msg} />
      ))}

      {isLoading && (
        <div className="flex justify-start gap-2.5 my-3">
          <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center flex-shrink-0 mt-1 shadow-sm">
            <Bot className="w-4 h-4" />
          </div>
          <div className="bg-white rounded-2xl rounded-tl-sm border border-slate-200 p-4 shadow-sm flex items-center gap-2 text-xs text-slate-500">
            <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
            <span>Consulting official NCDC guidelines and Gemini...</span>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
};

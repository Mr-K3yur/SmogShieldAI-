import React, { useState, useRef } from 'react';
import { Send, Loader2, ShieldCheck } from 'lucide-react';
import { SupportedLanguage } from '../../types';

interface MessageComposerProps {
  onSendMessage: (text: string) => void;
  isLoading: boolean;
  language: SupportedLanguage;
}

const MAX_CHARS = 1000;

export const MessageComposer: React.FC<MessageComposerProps> = ({
  onSendMessage,
  isLoading,
  language,
}) => {
  const [input, setInput] = useState<string>('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const charCount = input.length;
  const isOverLimit = charCount > MAX_CHARS;
  const canSubmit = input.trim().length > 0 && !isOverLimit && !isLoading;

  const placeholders: Record<SupportedLanguage, string> = {
    en: 'Ask about air quality, outdoor safety, child precautions, or commute options...',
    hi: 'वायु गुणवत्ता, बच्चों की सुरक्षा, मास्क या सुरक्षित यात्रा के बारे में पूछें...',
    hinglish: 'Ask about air quality, bachho ki safety, commute options, ya purifier advice...',
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (canSubmit) {
        handleSubmit();
      }
    }
  };

  const handleSubmit = () => {
    if (!canSubmit) return;
    const trimmed = input.trim();
    if (trimmed) {
      onSendMessage(trimmed);
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-adjust height up to max
    const target = e.target;
    target.style.height = 'auto';
    target.style.height = `${Math.min(target.scrollHeight, 160)}px`;
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-3 sm:p-4 shadow-sm transition-all space-y-2">
      {/* Input row */}
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          rows={2}
          maxLength={MAX_CHARS + 50} // slight buffer so user sees overflow
          placeholder={placeholders[language]}
          className="flex-1 resize-none bg-slate-50 focus:bg-white rounded-lg p-3 text-sm text-slate-800 placeholder-slate-400 border border-slate-200 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-all disabled:opacity-60"
          aria-label="Ask the AI assistant a question"
        />

        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSubmit}
          className={`h-11 px-4 rounded-lg flex items-center justify-center font-medium text-sm transition-all shadow-sm ${
            canSubmit
              ? 'bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer active:scale-95'
              : 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200'
          }`}
          aria-label="Send message to AI assistant"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Footer: Character Counter & Privacy Notice */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 text-xs text-slate-400 pt-1">
        <div className="flex items-center gap-1.5 text-[11px] text-slate-500 leading-tight">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
          <span>
            Your message and selected environmental parameters are processed by Google Gemini. Avoid entering names, addresses, or medical details.
          </span>
        </div>

        <div className={`text-[11px] font-mono self-end sm:self-auto ${isOverLimit ? 'text-rose-600 font-bold' : 'text-slate-400'}`}>
          {charCount} / {MAX_CHARS}
        </div>
      </div>
    </div>
  );
};

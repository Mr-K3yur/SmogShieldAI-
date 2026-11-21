import React from 'react';
import { Sparkles } from 'lucide-react';
import { SupportedLanguage } from '../../types';

interface QuickSuggestionsProps {
  language: SupportedLanguage;
  onSelectSuggestion: (question: string) => void;
  disabled?: boolean;
}

export const QuickSuggestions: React.FC<QuickSuggestionsProps> = ({
  language,
  onSelectSuggestion,
  disabled = false,
}) => {
  const suggestionsByLanguage: Record<SupportedLanguage, string[]> = {
    en: [
      'Can my children play outside today?',
      'How should I commute to work safely?',
      'How can I improve indoor air quality?',
      'Explain my room air purifier requirements.',
      'Explain my transport emissions.',
      'What does the current AQI category mean for my health?',
    ],
    hi: [
      'क्या आज बच्चे बाहर खेल सकते हैं?',
      'खराब वायु गुणवत्ता में सुरक्षित यात्रा कैसे करें?',
      'कमरे के एयर प्यूरीफायर की आवश्यकता समझाएं।',
      'घर के अंदर की वायु गुणवत्ता कैसे सुधारें?',
      'वर्तमान एक्यूआई का स्वास्थ्य पर क्या प्रभाव है?',
    ],
    hinglish: [
      'Kya aaj bachho ko outdoor sports bhejna theek hai?',
      'AQI ka matlab kya hai aur kya precautions lene chahiye?',
      'Office commute ke liye best transit option kya hai?',
      'Mere room ke liye air purifier CADR requirement kya hai?',
      'Transport CO2 emissions ko kaise reduce karein?',
    ],
  };

  const currentSuggestions = suggestionsByLanguage[language] || suggestionsByLanguage.en;

  return (
    <div className="space-y-2 py-2">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-600">
        <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
        <span>{language === 'hi' ? 'सुझाए गए प्रश्न' : language === 'hinglish' ? 'Suggested Questions' : 'Suggested Questions'}</span>
      </div>

      <div className="flex flex-wrap gap-2">
        {currentSuggestions.map((question, idx) => (
          <button
            key={idx}
            type="button"
            disabled={disabled}
            onClick={() => onSelectSuggestion(question)}
            className="text-left text-xs px-3 py-1.5 rounded-full bg-white hover:bg-emerald-50 text-slate-700 hover:text-emerald-800 border border-slate-200 hover:border-emerald-300 transition-all shadow-2xs disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-emerald-400"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
};

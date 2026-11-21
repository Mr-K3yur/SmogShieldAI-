import React from 'react';
import { AlertCircle, ShieldCheck } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-slate-900 border-t border-slate-800 text-slate-400 text-xs py-8 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-4">
        {/* Ethical Non-Medical Disclaimer */}
        <div className="bg-slate-800/80 border border-slate-700/60 rounded-lg p-3.5 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="text-slate-300 leading-relaxed text-xs">
            <span className="font-semibold text-amber-300">Public Health & Medical Disclaimer:</span> SmogShield AI provides environmental exposure guidance based on Central Pollution Control Board (CPCB) air quality standards and documented transport factors. It does not provide medical diagnoses, treatment prescriptions, or clinical advice. For acute respiratory symptoms, consult a qualified physician or pediatrician.
          </div>
        </div>

        {/* Footer info bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between pt-2 border-t border-slate-800/80 gap-3 text-slate-500">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            <span>SmogShield AI — Software Development Competition Edition</span>
          </div>
          <div className="text-center sm:text-right text-xs">
            <span>Powered by CPCB NAQI Standards • FastAPI • React & TypeScript • Google Gemini</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

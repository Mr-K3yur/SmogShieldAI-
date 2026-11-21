import React from 'react';
import { Home, Wind, Sparkles, CheckCircle2, XCircle } from 'lucide-react';

export const AdvisorPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 mb-2">
          <Home className="w-3.5 h-3.5" />
          Evidence-Based Indoor Safety
        </div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Indoor Air & Filtration Advisor</h1>
        <p className="text-sm text-slate-500 mt-1">
          Mechanical air purification sizing, low-cost DIY filtration, damp cleaning practices, and condition-based ventilation.
        </p>
      </div>

      {/* Grid of Key Indoor Pillars */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Pillar 1: CADR & Room Sizing */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-lg">
            <Wind className="w-5 h-5" />
          </div>
          <h2 className="text-base font-semibold text-slate-900">CADR & Room Sizing</h2>
          <p className="text-xs text-slate-500 leading-relaxed">
            Calculates required Clean Air Delivery Rate (m³/h) based on room volume and a target 4–5 Air Changes per Hour (ACH) for severe winter smog conditions.
          </p>
          <div className="text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100 font-mono">
            CADR (m³/h) = Area (m²) × Height (m) × ACH
          </div>
        </div>

        {/* Pillar 2: Low-Cost DIY Purifiers */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold text-lg">
            <Sparkles className="w-5 h-5" />
          </div>
          <h2 className="text-base font-semibold text-slate-900">Affordable DIY Purifiers</h2>
          <p className="text-xs text-slate-500 leading-relaxed">
            Assembling verified fan-filter systems (Corsi-Rosenthal principle) using a standard domestic table fan (50W) and MERV 13/HEPA pleated sheet for ₹1,500–₹2,200.
          </p>
          <div className="text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100">
            ~120 m³/h delivery at 1/10th the cost of commercial branded purifiers.
          </div>
        </div>

        {/* Pillar 3: Source Control & Plants Truth */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-3">
          <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center font-bold text-lg">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <h2 className="text-base font-semibold text-slate-900">Source Control & Facts</h2>
          <div className="space-y-2 text-xs text-slate-600">
            <div className="flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
              <span>Damp microfiber mopping avoids dust resuspension caused by dry brooms.</span>
            </div>
            <div className="flex items-start gap-2">
              <XCircle className="w-4 h-4 text-rose-500 flex-shrink-0 mt-0.5" />
              <span><strong>Plants Reality:</strong> Potted plants do not substitute for mechanical filtration of toxic PM2.5.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

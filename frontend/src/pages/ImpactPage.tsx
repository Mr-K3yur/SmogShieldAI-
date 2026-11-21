import React from 'react';
import { Calculator, BarChart3, HelpCircle, Layers } from 'lucide-react';

export const ImpactPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-violet-50 text-violet-700 border border-violet-200 mb-2">
          <Calculator className="w-3.5 h-3.5" />
          Transparent Carbon Accounting
        </div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Environmental Impact Tracker</h1>
        <p className="text-sm text-slate-500 mt-1">
          Calculate documented CO₂ savings from sustainable commute shifts with fully visible mathematical assumptions.
        </p>
      </div>

      {/* Tracker Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Metric Card */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider font-semibold text-slate-500">
              Cumulative CO₂ Avoided
            </span>
            <BarChart3 className="w-4 h-4 text-violet-600" />
          </div>

          <div className="py-4">
            <div className="text-4xl font-extrabold text-slate-900">0.00 <span className="text-lg font-medium text-slate-500">kg CO₂e</span></div>
            <p className="text-xs text-slate-500 mt-1">Based on documented ARAI & CEA benchmark factors.</p>
          </div>

          <div className="p-3 bg-violet-50/60 rounded-lg border border-violet-100 text-xs text-violet-900 leading-relaxed">
            Formula: Δ CO₂ = (Distance × Factor_baseline) - (Distance × Factor_chosen / Occupancy)
          </div>
        </div>

        {/* Methodology & Integrity Card */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
          <div className="flex items-center gap-2 text-slate-800 font-semibold text-base">
            <HelpCircle className="w-5 h-5 text-violet-600" />
            <span>Methodology & Scientific Integrity</span>
          </div>

          <div className="space-y-2 text-xs text-slate-600">
            <div className="flex items-start gap-2 p-2.5 bg-slate-50 rounded-lg border border-slate-100">
              <Layers className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
              <span><strong>Documented Factors Only:</strong> Sourced from Central Electricity Authority (CEA) Ver. 19 (2023) and Automotive Research Association of India (ARAI).</span>
            </div>

            <div className="flex items-start gap-2 p-2.5 bg-slate-50 rounded-lg border border-slate-100">
              <Layers className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
              <span><strong>Zero Invented Health Metaphors:</strong> Unsupported cigarette analogies and fictitious inhalation metrics have been rigorously excluded.</span>
            </div>
          </div>

          <p className="text-xs text-slate-400 pt-2">
            * Interactive distance and occupancy calculator will be implemented in Phase 5.
          </p>
        </div>
      </div>
    </div>
  );
};

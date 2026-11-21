import React from 'react';
import { 
  ShieldAlert, 
  AlertCircle, 
  Users, 
  Baby, 
  Bus, 
  Clock, 
  Sparkles,
  FileText 
} from 'lucide-react';
import { DeterministicAuthoritativeGuidance } from '../../types';

interface AuthoritativeGuidanceCardProps {
  guidance: DeterministicAuthoritativeGuidance | null | undefined;
}

export const AuthoritativeGuidanceCard: React.FC<AuthoritativeGuidanceCardProps> = ({ guidance }) => {
  if (!guidance) {
    return (
      <div className="bg-slate-50 rounded-xl border border-slate-200/80 p-5 text-center text-slate-500">
        <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-slate-100 text-slate-400 mb-2">
          <AlertCircle className="w-5 h-5" />
        </div>
        <h3 className="text-sm font-semibold text-slate-700">Authoritative Guidance Standby</h3>
        <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
          Current deterministic NCDC guidelines will populate here when environmental station data is attached or queried.
        </p>
      </div>
    );
  }

  // Visual categorization based on official CPCB category
  const categoryColorMap: Record<string, { bg: string; text: string; border: string; badgeBg: string }> = {
    Good: { bg: 'bg-emerald-50', text: 'text-emerald-900', border: 'border-emerald-200', badgeBg: 'bg-emerald-600 text-white' },
    Satisfactory: { bg: 'bg-lime-50', text: 'text-lime-900', border: 'border-lime-200', badgeBg: 'bg-lime-600 text-white' },
    Moderate: { bg: 'bg-amber-50', text: 'text-amber-900', border: 'border-amber-200', badgeBg: 'bg-amber-500 text-white' },
    Poor: { bg: 'bg-orange-50', text: 'text-orange-900', border: 'border-orange-200', badgeBg: 'bg-orange-600 text-white' },
    'Very Poor': { bg: 'bg-red-50', text: 'text-red-900', border: 'border-red-200', badgeBg: 'bg-red-600 text-white' },
    Severe: { bg: 'bg-rose-50', text: 'text-rose-950', border: 'border-rose-300', badgeBg: 'bg-rose-700 text-white' },
    Unknown: { bg: 'bg-slate-50', text: 'text-slate-800', border: 'border-slate-200', badgeBg: 'bg-slate-600 text-white' },
  };

  const style = categoryColorMap[guidance.applicable_aqi_category] || categoryColorMap.Unknown;

  return (
    <div className={`rounded-xl border ${style.border} ${style.bg} p-5 sm:p-6 shadow-sm transition-all`}>
      {/* Top Header: Badge, Category, Priority */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-200/60">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-slate-700 flex-shrink-0" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Official NCDC 2025 Public Health Advisory
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* AQI Category Badge */}
          <span className={`px-2.5 py-1 rounded-md text-xs font-bold ${style.badgeBg}`}>
            AQI Category: {guidance.applicable_aqi_category}
          </span>
          {/* Action Priority Badge */}
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-white/80 border border-slate-200 text-slate-800">
            Priority: {guidance.action_priority}
          </span>
        </div>
      </div>

      {/* Advisories Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 text-xs">
        {/* General Population Advisory */}
        <div className="bg-white/90 p-3.5 rounded-lg border border-slate-200/60 space-y-1">
          <div className="flex items-center gap-1.5 font-semibold text-slate-900">
            <Users className="w-4 h-4 text-slate-600" />
            <span>General Population</span>
          </div>
          <p className="text-slate-700 leading-relaxed">
            {guidance.general_population_advisory}
          </p>
        </div>

        {/* Vulnerable Population Advisory */}
        <div className="bg-white/90 p-3.5 rounded-lg border border-slate-200/60 space-y-1">
          <div className="flex items-center gap-1.5 font-semibold text-rose-900">
            <AlertCircle className="w-4 h-4 text-rose-600" />
            <span>Vulnerable Groups (Children, Seniors, Respiratory)</span>
          </div>
          <p className="text-slate-700 leading-relaxed">
            {guidance.vulnerable_population_advisory}
          </p>
        </div>

        {/* Schoolchildren Advisory (if present) */}
        {guidance.schoolchildren_advisory && (
          <div className="bg-white/90 p-3.5 rounded-lg border border-slate-200/60 space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-amber-900">
              <Baby className="w-4 h-4 text-amber-600" />
              <span>Schoolchildren & Sports</span>
            </div>
            <p className="text-slate-700 leading-relaxed">
              {guidance.schoolchildren_advisory}
            </p>
          </div>
        )}

        {/* Essential Travel Guidance (if present) */}
        {guidance.essential_travel_guidance && (
          <div className="bg-white/90 p-3.5 rounded-lg border border-slate-200/60 space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-blue-900">
              <Bus className="w-4 h-4 text-blue-600" />
              <span>Essential Commute & Transit</span>
            </div>
            <p className="text-slate-700 leading-relaxed">
              {guidance.essential_travel_guidance}
            </p>
          </div>
        )}
      </div>

      {/* Additional Protective Notes (Mask & Diurnal Timing) */}
      {(guidance.mask_protective_guidance || guidance.diurnal_timing_note) && (
        <div className="mt-3.5 pt-3 border-t border-slate-200/60 flex flex-wrap gap-3 text-xs text-slate-600">
          {guidance.mask_protective_guidance && (
            <div className="flex items-start gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-slate-500 mt-0.5 flex-shrink-0" />
              <span><strong>Mask Guidance:</strong> {guidance.mask_protective_guidance}</span>
            </div>
          )}
          {guidance.diurnal_timing_note && (
            <div className="flex items-start gap-1.5">
              <Clock className="w-3.5 h-3.5 text-slate-500 mt-0.5 flex-shrink-0" />
              <span><strong>Diurnal Window:</strong> {guidance.diurnal_timing_note}</span>
            </div>
          )}
        </div>
      )}

      {/* Official Citation Footer */}
      <div className="mt-3.5 pt-3 border-t border-slate-200/60 flex items-center justify-between text-[11px] text-slate-500">
        <span className="flex items-center gap-1">
          <FileText className="w-3 h-3 text-slate-400" />
          <span>Source: {guidance.source_citation}</span>
        </span>
        <span className="font-semibold text-slate-600">Deterministic Rule Engine</span>
      </div>
    </div>
  );
};

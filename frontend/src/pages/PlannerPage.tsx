import React from 'react';
import { CalendarClock, AlertTriangle, Users, Compass, BellRing } from 'lucide-react';

export const PlannerPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 mb-2">
          <CalendarClock className="w-3.5 h-3.5" />
          Condition-Based Scheduling
        </div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Personalized Daily Activity Planner</h1>
        <p className="text-sm text-slate-500 mt-1">
          Dynamic family routines adapted to verified local air quality measurements and official meteorological forecasts.
        </p>
      </div>

      {/* Routine Planning Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
          <div className="flex items-center gap-2 text-slate-800 font-semibold text-base">
            <Users className="w-5 h-5 text-blue-600" />
            <span>Family Composition & Priorities</span>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">
            Tailors daily guidance to school-age children (commute & outdoor physical education), working commuters, and sensitive family members without arbitrary arithmetic multipliers.
          </p>

          <div className="space-y-2 pt-2">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-700 flex justify-between items-center">
              <span className="font-medium">School Transit Guidance</span>
              <span className="text-slate-500 font-mono">Condition-based N95 trigger</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-700 flex justify-between items-center">
              <span className="font-medium">Recess & Outdoor Physical Ed.</span>
              <span className="text-slate-500 font-mono">CPCB Severe threshold sync</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-700 flex justify-between items-center">
              <span className="font-medium">Workplace Commute Timing</span>
              <span className="text-slate-500 font-mono">Transit exposure mitigation</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
          <div className="flex items-center gap-2 text-slate-800 font-semibold text-base">
            <Compass className="w-5 h-5 text-amber-600" />
            <span>Scientific Scheduling Principles</span>
          </div>
          
          <div className="space-y-3 text-xs text-slate-600">
            <div className="p-3 rounded-lg bg-amber-50/60 border border-amber-200/80 flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-amber-900">No Fixed "Safe" Assumptions:</span> Time slots are never declared unconditionally safe without verified live sensor readings or official IMD/CPCB forecasts.
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-start gap-2.5">
              <BellRing className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-slate-800">CPCB Health Warnings:</span> Recommendations align directly with national health categories (Good to Severe).
              </div>
            </div>
          </div>

          <div className="pt-2 text-xs text-slate-400">
            * Complete planner scheduling engine will be integrated in Phase 4.
          </div>
        </div>
      </div>
    </div>
  );
};

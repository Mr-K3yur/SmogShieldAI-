import React from 'react';
import { Leaf, Train, Car, Bike, ShieldCheck, ArrowRight } from 'lucide-react';

export const TransportPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 mb-2">
          <Leaf className="w-3.5 h-3.5" />
          Sustainable Urban Transit
        </div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Green Alternatives & Commute Navigator</h1>
        <p className="text-sm text-slate-500 mt-1">
          Compare transport emissions using verified ARAI & CEA factors, with qualitative in-transit exposure mitigation.
        </p>
      </div>

      {/* Transit Modes Comparison Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Mode 1: Electric Urban Rail */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
                <Train className="w-5 h-5" />
              </div>
              <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                18.2 g CO₂ / pass-km
              </span>
            </div>
            <h2 className="text-base font-bold text-slate-900">Delhi Metro & Electric Rail</h2>
            <p className="text-xs text-slate-500 mt-1">
              Documented CEA CO₂ Baseline Database Ver. 19.
            </p>
            <div className="mt-4 text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100">
              <span className="font-semibold text-slate-800">In-Transit Air Quality:</span> Enclosed AC coaches and station platform screen doors provide substantial isolation from street-level vehicular exhaust plumes.
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-emerald-700 font-medium flex items-center gap-1">
            <ShieldCheck className="w-4 h-4" /> Recommended for high-AQI days
          </div>
        </div>

        {/* Mode 2: Carpooling & CNG Bus */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center">
                <Car className="w-5 h-5" />
              </div>
              <span className="text-xs font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full">
                Occupancy-Weighted
              </span>
            </div>
            <h2 className="text-base font-bold text-slate-900">Carpooling & Public Bus</h2>
            <p className="text-xs text-slate-500 mt-1">
              ARAI passenger vehicle factors divided by vehicle occupancy.
            </p>
            <div className="mt-4 text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100">
              <span className="font-semibold text-slate-800">In-Transit Air Quality:</span> Enclosed AC cabin with internal air recirculation mode on reduces direct exhaust ingestion compared to open transit.
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-blue-700 font-medium flex items-center gap-1">
            <ArrowRight className="w-4 h-4" /> 2-4 passenger occupancy optimization
          </div>
        </div>

        {/* Mode 3: Two-Wheeler & Auto */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center">
                <Bike className="w-5 h-5" />
              </div>
              <span className="text-xs font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full">
                High Street Exposure
              </span>
            </div>
            <h2 className="text-base font-bold text-slate-900">Two-Wheelers & Auto-Rickshaws</h2>
            <p className="text-xs text-slate-500 mt-1">
              44.2 g CO₂/km (two-wheeler) • 64.5 g/km (CNG auto).
            </p>
            <div className="mt-4 text-xs text-slate-600 bg-amber-50/60 p-3 rounded-lg border border-amber-200/60">
              <span className="font-semibold text-amber-900">In-Transit Exposure Alert:</span> Riders are directly immersed in roadside exhaust plumes. High acute exposure to diesel soot and black carbon.
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-amber-800 font-medium">
            Requires well-fitted N95 particulate mask
          </div>
        </div>
      </div>
    </div>
  );
};

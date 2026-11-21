import React from 'react';
import { Activity, Radio, Clock, ShieldCheck, MapPin } from 'lucide-react';
import { BackendHealthResponse } from '../types';

interface DashboardPageProps {
  health: BackendHealthResponse | null;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ health }) => {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 mb-2">
            <Radio className="w-3.5 h-3.5 animate-pulse" />
            Verified Air Quality Hub
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Live AQI & Health Advisory</h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time CPCB National AQI, pollutant breakdown, and health risk advisories for urban families.
          </p>
        </div>

        {/* Selected City & Station Pill */}
        <div className="flex items-center gap-2 bg-slate-100 px-3 py-2 rounded-lg text-sm text-slate-700 border border-slate-200">
          <MapPin className="w-4 h-4 text-emerald-600" />
          <span className="font-medium">Anand Vihar, Delhi</span>
          <span className="text-xs text-slate-400">• CPCB Feed</span>
        </div>
      </div>

      {/* Feature Showcase Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Main AQI Dial Card */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs text-slate-500 mb-4">
              <span className="uppercase tracking-wider font-semibold">National AQI (CPCB)</span>
              <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
                <ShieldCheck className="w-3.5 h-3.5" /> Verified Station
              </span>
            </div>

            <div className="text-center py-6">
              <div className="inline-flex items-center justify-center w-28 h-28 rounded-full border-4 border-slate-200 bg-slate-50">
                <span className="text-3xl font-extrabold text-slate-800">--</span>
              </div>
              <p className="text-sm font-semibold text-slate-600 mt-3">Awaiting Live Ingestion</p>
              <p className="text-xs text-slate-400 mt-1">Configured for CPCB official breakpoint calculation</p>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-slate-400" /> Freshness: &lt; 2h
            </span>
            <span className="bg-slate-100 px-2 py-0.5 rounded text-slate-600">Phase 2 Ingestion</span>
          </div>
        </div>

        {/* Particulate Readings Cards */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900 mb-1">Key Pollutant Breakdown</h2>
            <p className="text-xs text-slate-500 mb-4">Averaging intervals per CPCB 2014 standards</p>

            <div className="space-y-3">
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 flex justify-between items-center">
                <div>
                  <div className="text-sm font-bold text-slate-800">PM2.5 (Fine Particulates)</div>
                  <div className="text-xs text-slate-400">24-hr standard: 60 µg/m³</div>
                </div>
                <div className="text-right">
                  <span className="text-base font-bold text-slate-700">--</span>
                  <span className="text-xs text-slate-400 ml-1">µg/m³</span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 flex justify-between items-center">
                <div>
                  <div className="text-sm font-bold text-slate-800">PM10 (Coarse Inhalables)</div>
                  <div className="text-xs text-slate-400">24-hr standard: 100 µg/m³</div>
                </div>
                <div className="text-right">
                  <span className="text-base font-bold text-slate-700">--</span>
                  <span className="text-xs text-slate-400 ml-1">µg/m³</span>
                </div>
              </div>
            </div>
          </div>

          <p className="text-xs text-slate-400 pt-4 border-t border-slate-100">
            Minimum 3-pollutant rule with mandatory PM component enforced.
          </p>
        </div>

        {/* Backend & Provenance Status */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900 mb-1">Engine & Provenance Status</h2>
            <p className="text-xs text-slate-500 mb-4">FastAPI runtime & data state tracking</p>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">FastAPI Engine:</span>
                <span className="font-semibold text-emerald-600 flex items-center gap-1">
                  <Activity className="w-3.5 h-3.5" /> {health?.status === 'healthy' ? 'Active' : 'Offline'}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">Configured AI Model:</span>
                <span className="font-mono text-slate-800 bg-slate-100 px-1.5 py-0.5 rounded">
                  {health?.gemini_model_configured || 'gemini-3.8-flash'}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">CPCB NAQI Rules:</span>
                <span className="font-medium text-slate-700">Strict Oct 2014 Criteria</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-slate-500">Data States:</span>
                <span className="text-slate-700">Reported | Calculated | Demo</span>
              </div>
            </div>
          </div>

          <div className="mt-4 p-2.5 bg-emerald-50 rounded-lg border border-emerald-100 text-xs text-emerald-800">
            ✓ Phase 1 project foundation active and verified.
          </div>
        </div>
      </div>
    </div>
  );
};

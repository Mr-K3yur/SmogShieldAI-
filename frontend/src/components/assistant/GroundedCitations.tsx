import React, { useState } from 'react';
import { ChevronDown, ChevronUp, FileCheck2, Database } from 'lucide-react';
import { GroundedCitation } from '../../types';

interface GroundedCitationsProps {
  citations: GroundedCitation[];
}

export const GroundedCitations: React.FC<GroundedCitationsProps> = ({ citations }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  if (!citations || citations.length === 0) {
    return null;
  }

  const provenanceBadge = (prov: string) => {
    switch (prov) {
      case 'PROVIDER_REPORTED':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800">PROVIDER_REPORTED</span>;
      case 'CALCULATED':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-100 text-blue-800">CALCULATED</span>;
      case 'SIMULATED_DEMO':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-purple-100 text-purple-800">SIMULATED_DEMO</span>;
      case 'USER_REPORTED':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">USER_REPORTED</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">{prov}</span>;
    }
  };

  const freshnessBadge = (fresh: string) => {
    switch (fresh) {
      case 'FRESH':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-green-50 text-green-700 border border-green-200">FRESH</span>;
      case 'STALE':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">STALE (&gt;4h)</span>;
      case 'EXPIRED':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">EXPIRED (&gt;24h)</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-50 text-slate-600 border border-slate-200">{fresh}</span>;
    }
  };

  return (
    <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50/70 overflow-hidden text-xs transition-all">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3.5 py-2 text-slate-700 hover:bg-slate-100/70 font-medium transition-colors focus:outline-none"
        aria-expanded={isExpanded}
        aria-label="Toggle grounded data citations panel"
      >
        <span className="flex items-center gap-1.5">
          <Database className="w-3.5 h-3.5 text-slate-500" />
          <span>Grounded Data Citations ({citations.length})</span>
        </span>
        <span className="flex items-center gap-1 text-[11px] text-slate-500">
          <span>{isExpanded ? 'Hide' : 'Show Details'}</span>
          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </span>
      </button>

      {isExpanded && (
        <div className="p-3 border-t border-slate-200 bg-white space-y-2">
          {citations.map((c, idx) => (
            <div
              key={`${c.metric_name}-${idx}`}
              className="p-2.5 rounded-md bg-slate-50 border border-slate-150 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
            >
              <div className="space-y-0.5">
                <div className="flex items-center gap-1.5 font-semibold text-slate-900">
                  <FileCheck2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>{c.metric_name}:</span>
                  <span className="text-slate-700 font-mono font-medium">{c.reported_value}</span>
                </div>
                <div className="text-[11px] text-slate-500">
                  Doc: <span className="text-slate-600">{c.citation_document}</span> ({c.source_service})
                </div>
              </div>

              <div className="flex items-center gap-1.5 flex-wrap">
                {provenanceBadge(c.provenance)}
                {freshnessBadge(c.freshness)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

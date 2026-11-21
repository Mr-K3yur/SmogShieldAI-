import React, { useEffect, useState, useCallback } from 'react';
import { 
  Activity, 
  Radio, 
  Clock, 
  ShieldCheck, 
  AlertTriangle, 
  RefreshCw, 
  MapPin, 
  Info,
  Server
} from 'lucide-react';
import { 
  BackendHealthResponse, 
  StationMetadata, 
  StationAQIResponse 
} from '../types';
import { aqiApi } from '../services/api';
import { getBandForCategory } from '../utils/cpcbColors';
import { formatConcentration, formatToIST } from '../utils/formatters';

interface DashboardPageProps {
  health: BackendHealthResponse | null;
  onSelectStation?: (stationId: string) => void;
  selectedStationId?: string;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ 
  health, 
  onSelectStation, 
  selectedStationId 
}) => {
  const [provider, setProvider] = useState<'cpcb_datagov' | 'mock'>('cpcb_datagov');
  const [stations, setStations] = useState<StationMetadata[]>([]);
  const [activeStationId, setActiveStationId] = useState<string>(selectedStationId || '');
  const [stationData, setStationData] = useState<StationAQIResponse | null>(null);
  const [isLoadingStations, setIsLoadingStations] = useState<boolean>(true);
  const [isLoadingReport, setIsLoadingReport] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [stationWarning, setStationWarning] = useState<string | null>(null);

  // 1. Load available stations from backend
  const loadStations = useCallback(async (selectedProvider: 'cpcb_datagov' | 'mock' = provider) => {
    setIsLoadingStations(true);
    setErrorMessage(null);
    setStationWarning(null);
    try {
      const response = await aqiApi.listStations({ provider: selectedProvider });
      const list = response.stations || [];
      setStations(list);

      if (list.length > 0) {
        const defaultId = (activeStationId && list.some(s => s.station_id === activeStationId))
          ? activeStationId
          : list[0].station_id;
        setActiveStationId(defaultId);
        if (onSelectStation) onSelectStation(defaultId);
      } else {
        setActiveStationId('');
        setStationData(null);
      }
      if (response.warnings && response.warnings.length > 0) {
        setStationWarning(response.warnings.join(' '));
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to discover monitoring stations.';
      setErrorMessage(msg);
    } finally {
      setIsLoadingStations(false);
    }
  }, [activeStationId, onSelectStation]);

  useEffect(() => {
    loadStations(provider);
  }, [provider]);

  // 2. Fetch air quality report whenever activeStationId changes
  const fetchReport = useCallback(async (stationId: string) => {
    if (!stationId) return;
    setIsLoadingReport(true);
    setErrorMessage(null);
    try {
      const report = await aqiApi.getStationAqi(stationId);
      setStationData(report);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : `Failed to load station air quality report.`;
      setErrorMessage(msg);
      setStationData(null);
    } finally {
      setIsLoadingReport(false);
    }
  }, []);

  useEffect(() => {
    if (activeStationId) {
      fetchReport(activeStationId);
    }
  }, [activeStationId, fetchReport]);

  const handleStationChange = (newStationId: string) => {
    setActiveStationId(newStationId);
    if (onSelectStation) {
      onSelectStation(newStationId);
    }
  };

  // Determine visual styling for CPCB health category
  const aqiBand = getBandForCategory(stationData?.category);
  const isAvailable = stationData?.availability === 'AVAILABLE';
  const isDemo = stationData?.provenance === 'SIMULATED_DEMO' || stationData?.freshness === 'DEMO';
  const isStale = stationData?.freshness === 'STALE';
  const isExpired = stationData?.freshness === 'EXPIRED';

  // Format AQI display
  const displayAqiScore = (): string => {
    if (!stationData || !isAvailable) return '--';
    if (stationData.overall_aqi !== null && stationData.overall_aqi !== undefined) {
      return String(stationData.overall_aqi);
    }
    if (stationData.overall_aqi_lower_bound && stationData.overall_aqi_upper_bound) {
      return `${stationData.overall_aqi_lower_bound}–${stationData.overall_aqi_upper_bound}`;
    }
    return '--';
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Error Alerts */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start justify-between gap-3 shadow-sm">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Unable to fetch air quality data</p>
              <p className="text-xs text-rose-700 mt-0.5">{errorMessage}</p>
            </div>
          </div>
          <button
            onClick={() => activeStationId ? fetchReport(activeStationId) : loadStations()}
            className="px-3 py-1 bg-rose-100 hover:bg-rose-200 text-rose-800 rounded-lg text-xs font-semibold transition"
          >
            Retry
          </button>
        </div>
      )}

      {/* Demo Mode / Warning Alert */}
      {(isDemo || stationWarning || (stations.length === 0 && !isLoadingStations)) && (
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start justify-between gap-3 shadow-sm">
          <div className="flex items-start gap-2.5">
            <Info className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-semibold">Provider & Ingestion Notice</p>
              <p className="text-amber-800">
                {isDemo 
                  ? 'Displaying offline simulated data for verification. This station is marked as SIMULATED_DEMO and is not live CPCB sensor telemetry.'
                  : stationWarning || 'No stations currently active for this provider.'}
              </p>
            </div>
          </div>
          {provider === 'cpcb_datagov' && stations.length === 0 && !isLoadingStations && (
            <button
              onClick={() => setProvider('mock')}
              className="px-3 py-1.5 bg-amber-200 hover:bg-amber-300 text-amber-950 font-bold rounded-lg text-xs whitespace-nowrap transition"
            >
              Load Demo Stations (6)
            </button>
          )}
        </div>
      )}

      {/* Header & Station Selector */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 mb-2">
            <Radio className="w-3.5 h-3.5 animate-pulse text-emerald-600" />
            Verified Air Quality Ingestion
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Live National AQI Hub</h1>
          <p className="text-sm text-slate-500 mt-1">
            Official Indian CPCB National Air Quality Index (NAQI 2014) computed from verified monitoring telemetry.
          </p>
        </div>

        {/* Station Dropdown & Controls */}
        <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto">
          {/* Feed Switch */}
          <div className="inline-flex rounded-lg border border-slate-200 p-0.5 text-xs bg-slate-50">
            <button
              type="button"
              onClick={() => setProvider('cpcb_datagov')}
              className={`px-2.5 py-1.5 rounded font-medium transition ${provider === 'cpcb_datagov' ? 'bg-white shadow-xs text-emerald-800 font-bold' : 'text-slate-500 hover:text-slate-800'}`}
            >
              Live Feed
            </button>
            <button
              type="button"
              onClick={() => setProvider('mock')}
              className={`px-2.5 py-1.5 rounded font-medium transition ${provider === 'mock' ? 'bg-white shadow-xs text-purple-800 font-bold' : 'text-slate-500 hover:text-slate-800'}`}
            >
              Demo Feed
            </button>
          </div>

          <div className="relative flex-1 md:w-64">
            <label htmlFor="station-select" className="sr-only">Select Monitoring Station</label>
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <MapPin className="w-4 h-4 text-emerald-600" />
            </div>
            <select
              id="station-select"
              value={activeStationId}
              onChange={(e) => handleStationChange(e.target.value)}
              disabled={isLoadingStations || stations.length === 0}
              className="w-full pl-9 pr-8 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition disabled:opacity-60"
            >
              {isLoadingStations ? (
                <option value="">Discovering stations...</option>
              ) : stations.length === 0 ? (
                <option value="">No stations discovered</option>
              ) : (
                stations.map((stn) => (
                  <option key={stn.station_id} value={stn.station_id}>
                    {stn.station_name} ({stn.city}) [{stn.provider}]
                  </option>
                ))
              )}
            </select>
          </div>

          <button
            onClick={() => fetchReport(activeStationId)}
            disabled={isLoadingReport || !activeStationId}
            title="Refresh current station data"
            className="p-2.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 transition disabled:opacity-50 flex items-center justify-center"
          >
            <RefreshCw className={`w-4 h-4 ${isLoadingReport ? 'animate-spin text-emerald-600' : ''}`} />
          </button>
        </div>
      </div>

      {/* Main Showcase Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card 1: Official National AQI Dial */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs text-slate-500 mb-4">
              <span className="uppercase tracking-wider font-semibold text-slate-700">CPCB National AQI</span>
              <span className={`inline-flex items-center gap-1 font-semibold px-2 py-0.5 rounded-full text-xs ${
                isDemo 
                  ? 'bg-amber-100 text-amber-800' 
                  : isAvailable 
                  ? 'bg-emerald-50 text-emerald-700' 
                  : 'bg-slate-100 text-slate-600'
              }`}>
                <ShieldCheck className="w-3.5 h-3.5" />
                {stationData?.provenance || 'INGESTING'}
              </span>
            </div>

            <div className="text-center py-6">
              {isLoadingReport ? (
                <div className="inline-flex items-center justify-center w-32 h-32 rounded-full border-4 border-slate-200 bg-slate-50 animate-pulse">
                  <RefreshCw className="w-8 h-8 text-slate-400 animate-spin" />
                </div>
              ) : (
                <div 
                  className="inline-flex flex-col items-center justify-center w-32 h-32 rounded-full border-4 shadow-inner transition-colors duration-300"
                  style={{
                    backgroundColor: aqiBand.bgHex,
                    borderColor: aqiBand.bgHex,
                    color: aqiBand.textHex,
                  }}
                >
                  <span className="text-4xl font-black tracking-tight">{displayAqiScore()}</span>
                  <span className="text-[10px] font-bold uppercase tracking-wider mt-0.5 opacity-90">
                    {stationData?.category || 'Unknown'}
                  </span>
                </div>
              )}

              <div className="mt-4">
                <h3 className="text-lg font-bold text-slate-900">
                  {stationData?.station?.station_name || 'Select Monitoring Station'}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Dominant Driver:{' '}
                  <span className="font-semibold text-slate-800">
                    {stationData?.dominant_pollutant || 'None identified'}
                  </span>
                </p>
              </div>

              {/* Advisory note */}
              <div className="mt-4 p-3 rounded-lg bg-slate-50 border border-slate-100 text-xs text-slate-700 text-left">
                <span className="font-semibold text-slate-900">Health Advisory: </span>
                {aqiBand.advisory}
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              Freshness:{' '}
              <span className={`font-semibold ${
                isExpired ? 'text-rose-600' : isStale ? 'text-amber-600' : 'text-emerald-700'
              }`}>
                {stationData?.freshness || 'FRESH'}
              </span>
            </span>
            <span className="text-slate-400 text-[11px]">
              {stationData?.observed_at_ist 
                ? `Observed ${formatToIST(stationData.observed_at_ist)}`
                : stationData?.observed_at_utc 
                ? `UTC: ${formatToIST(stationData.observed_at_utc)}`
                : 'Awaiting timestamp'}
            </span>
          </div>
        </div>

        {/* Card 2: Monitored Pollutant Breakdown */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-base font-bold text-slate-900">Pollutant Concentration Streams</h2>
              <span className="text-[11px] font-semibold bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                CPCB 2014 Linear
              </span>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Real-time sensor telemetry with individual sub-index evaluation.
            </p>

            {isLoadingReport ? (
              <div className="space-y-2 py-4">
                {[1, 2, 3].map((n) => (
                  <div key={n} className="h-12 bg-slate-100 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : stationData?.pollutant_measurements && Object.keys(stationData.pollutant_measurements).length > 0 ? (
              <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                {Object.entries(stationData.pollutant_measurements).map(([pollutant, item]) => (
                  <div 
                    key={pollutant} 
                    className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-between hover:bg-slate-100/70 transition"
                  >
                    <div>
                      <div className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                        <span>{pollutant}</span>
                        {item.sensor_id && (
                          <span className="text-[10px] text-slate-400 font-normal">#{item.sensor_id}</span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {item.averaging_period_hours}h avg • {item.source}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-black text-slate-900">
                        {formatConcentration(item.value, item.unit)}
                      </div>
                      <div className="text-[10px] text-slate-500">
                        Status: <span className="text-emerald-700 font-medium">{item.freshness}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-10 bg-slate-50 rounded-lg border border-dashed border-slate-200 text-xs text-slate-400">
                No raw pollutant measurements recorded for this station.
              </div>
            )}
          </div>

          <div className="pt-4 border-t border-slate-100 text-[11px] text-slate-500 flex items-center justify-between">
            <span>Minimum 3 pollutants rule required</span>
            <span className="font-semibold text-slate-700">Mandatory PM2.5 / PM10</span>
          </div>
        </div>

        {/* Card 3: Backend Ingestion & Provenance Audit */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-base font-bold text-slate-900">Ingestion & Audit Trail</h2>
              <Server className="w-4 h-4 text-slate-400" />
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Provenance verification and runtime calculation health.
            </p>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">FastAPI Backend:</span>
                <span className="font-semibold text-emerald-600 flex items-center gap-1">
                  <Activity className="w-3.5 h-3.5" /> 
                  {health?.status === 'healthy' ? 'Active (Render)' : 'Connecting...'}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">Provider Source:</span>
                <span className="font-medium text-slate-800">
                  {stationData?.source || 'CPCB / data.gov.in'}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">Station Identifier:</span>
                <span className="font-mono text-slate-700 bg-slate-100 px-1 rounded text-[11px]">
                  {stationData?.station?.station_id || activeStationId || 'None'}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">Provider-Reported AQI:</span>
                <span className="font-semibold text-slate-800">
                  {stationData?.provider_reported_aqi !== null && stationData?.provider_reported_aqi !== undefined 
                    ? `${stationData.provider_reported_aqi} (${stationData.provider_reported_category || 'N/A'})`
                    : 'Not published upstream'}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">Local CPCB NAQI Engine:</span>
                <span className="font-semibold text-emerald-700">
                  {stationData?.calculated_aqi !== null && stationData?.calculated_aqi !== undefined
                    ? `${stationData.calculated_aqi}`
                    : 'Evaluated from verified raw streams'}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">Configured AI Model:</span>
                <span className="font-mono text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded text-[11px]">
                  {health?.gemini_model_configured || 'gemini-3.8-flash'}
                </span>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 text-xs text-slate-500">
            {stationData?.unavailable_reason ? (
              <p className="text-rose-600 font-medium">Notice: {stationData.unavailable_reason}</p>
            ) : (
              <p className="text-slate-400 text-[11px]">
                Strict October 2014 CPCB breakpoint algorithm executed deterministically.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

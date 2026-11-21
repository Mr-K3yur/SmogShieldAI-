import React, { useState, useEffect, useCallback } from 'react';
import {
  Calculator,
  AlertTriangle,
  PlusCircle,
  RefreshCw,
  Info,
  CheckCircle2,
  History
} from 'lucide-react';
import {
  TransportMode,
  FuelType,
  TripLogEntry,
  ImpactSessionSummary,
  SessionCreationResponse,
} from '../types';
import { impactApi } from '../services/api';

export const ImpactPage: React.FC = () => {
  // Session state
  const [session, setSession] = useState<SessionCreationResponse | null>(null);
  const [summary, setSummary] = useState<ImpactSessionSummary | null>(null);
  const [isLoadingSession, setIsLoadingSession] = useState<boolean>(false);
  const [isLoadingSummary, setIsLoadingSummary] = useState<boolean>(false);
  const [isLoggingTrip, setIsLoggingTrip] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Trip Logging Form
  const [tripMode, setTripMode] = useState<TransportMode>('metro');
  const [tripDistance, setTripDistance] = useState<number>(10);
  const [tripRoundTrip, setTripRoundTrip] = useState<boolean>(false);
  const [tripOccupancy, setTripOccupancy] = useState<number>(1);
  const [includeBaseline, setIncludeBaseline] = useState<boolean>(true);
  const [baselineMode, setBaselineMode] = useState<TransportMode>('petrol_car');
  const [baselineFuel, setBaselineFuel] = useState<FuelType>('petrol');
  const [baselineOccupancy, setBaselineOccupancy] = useState<number>(1);
  const [tripNotes, setTripNotes] = useState<string>('');

  // 1. Initialize or restore session
  const initializeSession = useCallback(async () => {
    setIsLoadingSession(true);
    setErrorMessage(null);
    try {
      // Check if session ID was cached in browser memory for active session
      const cachedId = sessionStorage.getItem('smogshield_impact_session_id');
      if (cachedId) {
        try {
          const sum = await impactApi.getSessionSummary(cachedId);
          setSummary(sum);
          setSession({
            session_id: cachedId,
            created_at_utc: sum.created_at_utc,
            expires_at_utc: sum.expires_at_utc,
            storage_disclaimer: sum.storage_disclaimer,
          });
          setIsLoadingSession(false);
          return;
        } catch {
          // Session expired or server restarted, create new one below
          sessionStorage.removeItem('smogshield_impact_session_id');
        }
      }

      // Create new session
      const newSession = await impactApi.createSession();
      setSession(newSession);
      sessionStorage.setItem('smogshield_impact_session_id', newSession.session_id);

      // Fetch summary
      const sum = await impactApi.getSessionSummary(newSession.session_id);
      setSummary(sum);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to establish tracking session.';
      setErrorMessage(msg);
    } finally {
      setIsLoadingSession(false);
    }
  }, []);

  useEffect(() => {
    initializeSession();
  }, [initializeSession]);

  // Refresh summary
  const refreshSummary = async () => {
    if (!session?.session_id) return;
    setIsLoadingSummary(true);
    try {
      const sum = await impactApi.getSessionSummary(session.session_id);
      setSummary(sum);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to refresh session summary.';
      setErrorMessage(msg);
    } finally {
      setIsLoadingSummary(false);
    }
  };

  // Handle logging a completed trip
  const handleLogTrip = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session?.session_id) {
      setErrorMessage('Active session missing. Creating a new session...');
      initializeSession();
      return;
    }

    setIsLoggingTrip(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    const entry: TripLogEntry = {
      mode: tripMode,
      distance_km: tripDistance,
      round_trip: tripRoundTrip,
      occupancy: tripOccupancy,
      notes: tripNotes.trim() ? tripNotes.trim() : null,
      baseline_scenario: includeBaseline
        ? {
            mode: baselineMode,
            fuel_type: baselineFuel,
            occupancy: baselineOccupancy,
          }
        : null,
    };

    try {
      const res = await impactApi.logTrip(entry, session.session_id);
      setSuccessMessage(res.message || 'Trip logged successfully. Server-calculated emissions updated.');
      setTripNotes('');
      // Refresh summary
      await refreshSummary();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to record completed trip.';
      setErrorMessage(msg);
    } finally {
      setIsLoggingTrip(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-violet-50 text-violet-700 border border-violet-200 mb-2">
            <Calculator className="w-3.5 h-3.5" />
            Transparent Server-Side Carbon Accounting
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Environmental Impact Tracker</h1>
          <p className="text-sm text-slate-500 mt-1">
            Log completed sustainable commutes with 100% server-side mathematical verification and in-memory session security.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={initializeSession}
            disabled={isLoadingSession}
            className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition flex items-center gap-1.5"
            title="Start new isolated session"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingSession ? 'animate-spin' : ''}`} />
            New Session
          </button>
        </div>
      </div>

      {/* Messages */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start gap-3 shadow-sm">
          <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Session or Calculation Error</p>
            <p className="text-xs text-rose-700 mt-0.5">{errorMessage}</p>
          </div>
        </div>
      )}

      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-start gap-3 shadow-sm">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Trip Verified & Recorded</p>
            <p className="text-xs text-emerald-700 mt-0.5">{successMessage}</p>
          </div>
        </div>
      )}

      {/* In-Memory Session Lifetime Disclosure */}
      <div className="p-4 bg-amber-50/70 border border-amber-200/80 rounded-xl text-xs text-amber-900 space-y-1">
        <div className="flex items-center gap-1.5 font-bold">
          <Info className="w-4 h-4 text-amber-700" />
          <span>In-Memory Session Architecture & Disclaimers</span>
        </div>
        <p className="text-[11px] text-amber-800 leading-relaxed">
          {session?.storage_disclaimer || (
            <>
              Trip history is stored in temporary server memory and is not permanently persisted. Data will reset if the server restarts or expires after 24 hours of inactivity. All carbon calculations are computed exclusively on the backend.
            </>
          )}
        </p>
        {session && (
          <p className="text-[10px] text-amber-700 font-mono pt-0.5">
            Session ID: {session.session_id.substring(0, 8)}... (Bearer Token)
          </p>
        )}
      </div>

      {/* Main Grid: Form + Cumulative Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Form: Log Completed Trip (1 col) */}
        <div className="lg:col-span-1 bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-5">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <PlusCircle className="w-5 h-5 text-violet-600" />
            <h2 className="text-base font-bold text-slate-900">Log Completed Trip</h2>
          </div>

          <form onSubmit={handleLogTrip} className="space-y-4 text-xs">
            {/* Completed Transport Mode */}
            <div>
              <label htmlFor="trip-mode" className="block font-semibold text-slate-700 mb-1">
                Completed Travel Mode *
              </label>
              <select
                id="trip-mode"
                value={tripMode}
                onChange={(e) => setTripMode(e.target.value as TransportMode)}
                className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
              >
                <option value="metro">Delhi Metro / Urban Rail</option>
                <option value="intracity_bus">Intracity Public Bus</option>
                <option value="carpool">Shared Carpooling</option>
                <option value="electric_vehicle">Electric Car (EV)</option>
                <option value="cng_auto">CNG Auto-Rickshaw</option>
                <option value="cycling">Cycling (Zero Emission)</option>
                <option value="walking">Walking (Zero Emission)</option>
                <option value="petrol_motorcycle">Two-Wheeler</option>
                <option value="petrol_car">Private Petrol Car</option>
                <option value="diesel_car">Private Diesel Car</option>
              </select>
            </div>

            {/* Distance & Occupancy */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="trip-km" className="block font-semibold text-slate-700 mb-1">
                  Distance (km) *
                </label>
                <input
                  id="trip-km"
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="200"
                  value={tripDistance}
                  onChange={(e) => setTripDistance(parseFloat(e.target.value) || 0)}
                  required
                  className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                />
              </div>

              <div>
                <label htmlFor="trip-occ" className="block font-semibold text-slate-700 mb-1">
                  Occupancy
                </label>
                <input
                  id="trip-occ"
                  type="number"
                  min="1"
                  max={tripMode === 'cng_auto' ? 3 : 9}
                  value={tripOccupancy}
                  onChange={(e) => setTripOccupancy(parseInt(e.target.value, 10) || 1)}
                  className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                />
              </div>
            </div>

            {/* Round trip */}
            <label className="flex items-center gap-2 p-2 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer">
              <input
                type="checkbox"
                checked={tripRoundTrip}
                onChange={(e) => setTripRoundTrip(e.target.checked)}
                className="rounded text-violet-600 focus:ring-violet-500"
              />
              <span className="font-semibold text-slate-700">Trip was Round-Trip</span>
            </label>

            {/* Baseline Scenario Toggle */}
            <div className="pt-2 border-t border-slate-100 space-y-2">
              <label className="flex items-center justify-between p-2 rounded-lg bg-violet-50/50 border border-violet-100 cursor-pointer">
                <span className="font-semibold text-violet-900">Compare Against Baseline Mode</span>
                <input
                  type="checkbox"
                  checked={includeBaseline}
                  onChange={(e) => setIncludeBaseline(e.target.checked)}
                  className="rounded text-violet-600 focus:ring-violet-500"
                />
              </label>

              {includeBaseline && (
                <div className="space-y-2.5 p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <div>
                    <label htmlFor="base-mode" className="block font-semibold text-slate-700 mb-0.5">
                      Baseline Replaced Mode
                    </label>
                    <select
                      id="base-mode"
                      value={baselineMode}
                      onChange={(e) => setBaselineMode(e.target.value as TransportMode)}
                      className="w-full px-2 py-1 bg-white border border-slate-200 rounded text-slate-800"
                    >
                      <option value="petrol_car">Private Petrol Car</option>
                      <option value="diesel_car">Private Diesel Car</option>
                      <option value="petrol_motorcycle">Two-Wheeler (Petrol)</option>
                      <option value="cng_auto">CNG Auto-Rickshaw</option>
                    </select>
                  </div>

                  {(baselineMode === 'petrol_car' || baselineMode === 'diesel_car') && (
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label htmlFor="base-fuel" className="block font-semibold text-slate-700 mb-0.5">
                          Baseline Fuel
                        </label>
                        <select
                          id="base-fuel"
                          value={baselineFuel}
                          onChange={(e) => setBaselineFuel(e.target.value as FuelType)}
                          className="w-full px-2 py-1 bg-white border border-slate-200 rounded text-slate-800"
                        >
                          <option value="petrol">Petrol</option>
                          <option value="diesel">Diesel</option>
                        </select>
                      </div>
                      <div>
                        <label htmlFor="base-occ" className="block font-semibold text-slate-700 mb-0.5">
                          Baseline Occupancy
                        </label>
                        <input
                          id="base-occ"
                          type="number"
                          min="1"
                          max="9"
                          value={baselineOccupancy}
                          onChange={(e) => setBaselineOccupancy(parseInt(e.target.value, 10) || 1)}
                          className="w-full px-2 py-1 bg-white border border-slate-200 rounded text-slate-800"
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Optional Notes */}
            <div>
              <label htmlFor="trip-notes" className="block font-semibold text-slate-700 mb-1">
                Notes (Optional)
              </label>
              <input
                id="trip-notes"
                type="text"
                placeholder="e.g. Office commute via Yellow Line"
                value={tripNotes}
                onChange={(e) => setTripNotes(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
              />
            </div>

            <button
              type="submit"
              disabled={isLoggingTrip || !session}
              className="w-full mt-3 py-2.5 px-4 bg-violet-600 hover:bg-violet-700 text-white text-xs font-semibold rounded-lg shadow-sm hover:shadow transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoggingTrip ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Recording & Verifying on Server...
                </>
              ) : (
                <>
                  <PlusCircle className="w-3.5 h-3.5" />
                  Log Completed Trip
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Output: Cumulative Verified Metrics & Trip Log (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Cumulative Metrics Card */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <span className="text-xs uppercase tracking-wider font-semibold text-slate-500">
                Verified Session Carbon Account
              </span>
              <button
                onClick={refreshSummary}
                disabled={isLoadingSummary || !session}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded transition"
                title="Refresh summary"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingSummary ? 'animate-spin' : ''}`} />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 bg-violet-50/60 rounded-xl border border-violet-100">
                <span className="text-xs text-violet-800 font-semibold block">Avoided Passenger CO₂</span>
                <div className="text-3xl font-black text-violet-950 mt-1">
                  {summary?.actual_avoided_kg_co2?.toFixed(2) || '0.00'}{' '}
                  <span className="text-sm font-semibold text-violet-700">kg CO₂</span>
                </div>
                <span className="text-[10px] text-violet-600 mt-1 block">
                  Compared against replaced baseline
                </span>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-xs text-slate-500 font-semibold block">Total Incurred Tailpipe CO₂</span>
                <div className="text-3xl font-black text-slate-800 mt-1">
                  {summary?.actual_total_emissions_kg_co2?.toFixed(2) || '0.00'}{' '}
                  <span className="text-sm font-semibold text-slate-500">kg CO₂</span>
                </div>
                <span className="text-[10px] text-slate-400 mt-1 block">
                  Operational passenger emissions
                </span>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-xs text-slate-500 font-semibold block">Trips Logged</span>
                <div className="text-3xl font-black text-slate-800 mt-1">
                  {summary?.completed_action_count || 0}{' '}
                  <span className="text-sm font-semibold text-slate-500">trips</span>
                </div>
                <span className="text-[10px] text-slate-400 mt-1 block">
                  Isolated in active memory session
                </span>
              </div>
            </div>

            {/* Emissions by Mode Breakdown */}
            {summary?.emissions_by_mode && Object.keys(summary.emissions_by_mode).length > 0 && (
              <div className="pt-2 border-t border-slate-100">
                <span className="text-xs font-semibold text-slate-700 block mb-2">Emissions by Travel Mode</span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {Object.entries(summary.emissions_by_mode).map(([mode, kg]) => (
                    <div key={mode} className="p-2 bg-slate-50 rounded border border-slate-100 text-xs">
                      <span className="font-semibold text-slate-700 capitalize block truncate">
                        {mode.replace(/_/g, ' ')}
                      </span>
                      <span className="font-mono text-slate-900 font-bold">{kg.toFixed(3)} kg</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Recorded Trip History Table */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <History className="w-5 h-5 text-violet-600" />
                <h3 className="text-base font-bold text-slate-900">Recorded Trip History (This Session)</h3>
              </div>
              <span className="text-xs text-slate-400">Idempotency-Protected</span>
            </div>

            {summary?.completed_trips && summary.completed_trips.length > 0 ? (
              <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
                {summary.completed_trips.map((trip) => (
                  <div
                    key={trip.trip_id}
                    className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 hover:border-slate-300 transition text-xs space-y-1.5"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="font-bold text-slate-900 capitalize text-sm">
                          {trip.mode.replace(/_/g, ' ')}
                        </span>
                        <span className="text-slate-500 ml-2">
                          {trip.effective_distance_km} km ({trip.round_trip ? 'Round Trip' : 'One Way'})
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="font-black text-slate-800">
                          {trip.passenger_emissions_kg_co2.toFixed(3)} kg CO₂
                        </span>
                        {trip.actual_avoided_kg_co2 !== null && trip.actual_avoided_kg_co2 !== undefined && (
                          <span className="block text-emerald-700 font-bold text-[11px]">
                            Avoided: {trip.actual_avoided_kg_co2.toFixed(3)} kg
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-200/60">
                      <span>Factor Applied: #{trip.factor_id_used}</span>
                      {trip.notes && <span className="text-slate-600 italic font-medium">"{trip.notes}"</span>}
                      <span>Key: {trip.idempotency_key.substring(0, 8)}...</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-10 bg-slate-50 rounded-lg border border-dashed border-slate-200 text-xs text-slate-400">
                No trips logged yet in this session. Log a completed trip using the form on the left.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

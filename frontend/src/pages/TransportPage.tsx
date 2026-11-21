import React, { useState, useEffect } from 'react';
import {
  Leaf,
  Car,
  ArrowRight,
  AlertTriangle,
  RefreshCw,
  Sparkles,
  CheckCircle,
  Database
} from 'lucide-react';
import {
  TransportMode,
  FuelType,
  TransportComparisonRequest,
  TransportComparisonResponse,
  EmissionFactorEntry,
  StationMetadata,
} from '../types';
import { aqiApi, transportApi } from '../services/api';
import { getBandForCategory } from '../utils/cpcbColors';

interface TransportPageProps {
  selectedStationId?: string;
  onNavigateToImpact?: () => void;
}

export const TransportPage: React.FC<TransportPageProps> = ({ 
  selectedStationId,
  onNavigateToImpact 
}) => {
  // Station state
  const [stations, setStations] = useState<StationMetadata[]>([]);
  const [stationId, setStationId] = useState<string>(selectedStationId || '');

  // Commute Inputs
  const [currentMode, setCurrentMode] = useState<TransportMode>('petrol_car');
  const [fuelType, setFuelType] = useState<FuelType>('petrol');
  const [distanceKm, setDistanceKm] = useState<number>(12);
  const [roundTrip, setRoundTrip] = useState<boolean>(true);
  const [occupancy, setOccupancy] = useState<number>(1);
  const [tripsPerWeek, setTripsPerWeek] = useState<number>(5);

  // Selected alternatives
  const [selectedAlternatives, setSelectedAlternatives] = useState<TransportMode[]>([
    'metro',
    'intracity_bus',
    'carpool',
    'electric_vehicle',
  ]);

  // Comparison Results
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [comparisonResult, setComparisonResult] = useState<TransportComparisonResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Emission Factor Registry state
  const [showRegistry, setShowRegistry] = useState<boolean>(false);
  const [factors, setFactors] = useState<EmissionFactorEntry[]>([]);
  const [isLoadingFactors, setIsLoadingFactors] = useState<boolean>(false);

  // Load stations on mount
  useEffect(() => {
    let isMounted = true;
    async function loadStations() {
      try {
        let res = await aqiApi.listStations();
        if (res.stations.length === 0) {
          res = await aqiApi.listStations({ provider: 'mock' });
        }
        if (isMounted && res.stations && res.stations.length > 0) {
          setStations(res.stations);
          if (!stationId) {
            setStationId(res.stations[0].station_id);
          }
        }
      } catch {
        // Fallback
      }
    }
    loadStations();
    return () => {
      isMounted = false;
    };
  }, []);

  // Sync station ID
  useEffect(() => {
    if (selectedStationId) {
      setStationId(selectedStationId);
    }
  }, [selectedStationId]);

  // Load factors if drawer opened
  const loadEmissionFactors = async () => {
    if (factors.length > 0) return;
    setIsLoadingFactors(true);
    try {
      const res = await transportApi.getEmissionFactors();
      setFactors(res.factors || []);
    } catch {
      // Ignored
    } finally {
      setIsLoadingFactors(false);
    }
  };

  const handleToggleAlternative = (mode: TransportMode) => {
    setSelectedAlternatives((prev) => {
      if (prev.includes(mode)) {
        if (prev.length <= 1) return prev; // keep at least 1
        return prev.filter((m) => m !== mode);
      }
      return [...prev, mode];
    });
  };

  const handleCompareSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stationId) {
      setErrorMessage('Please select a monitoring station for live air quality context.');
      return;
    }

    if (selectedAlternatives.length === 0) {
      setErrorMessage('Please select at least one alternative transport mode to evaluate.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    const payload: TransportComparisonRequest = {
      station_id: stationId,
      current_mode: currentMode,
      fuel_type: currentMode === 'petrol_car' || currentMode === 'diesel_car' ? fuelType : null,
      distance_km: distanceKm,
      round_trip: roundTrip,
      occupancy: occupancy,
      trips_per_week: tripsPerWeek,
      alternatives: selectedAlternatives,
    };

    try {
      const response = await transportApi.compare(payload);
      setComparisonResult(response);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to compare transport emissions.';
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const aqiBand = getBandForCategory(comparisonResult?.aqi_category);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 mb-2">
            <Leaf className="w-3.5 h-3.5" />
            Deterministic GHG & Transit Exposure Engine
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Green Alternatives & Commute Navigator</h1>
          <p className="text-sm text-slate-500 mt-1">
            Compare passenger tailpipe CO₂ emissions using audited India GHG Program & CEA factors with NCDC in-transit exposure warnings.
          </p>
        </div>

        <button
          onClick={() => {
            setShowRegistry(!showRegistry);
            loadEmissionFactors();
          }}
          className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition flex items-center gap-2"
        >
          <Database className="w-4 h-4 text-emerald-600" />
          {showRegistry ? 'Hide Registry Factors' : 'Audited Factors (9)'}
        </button>
      </div>

      {/* Error alert */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start gap-3 shadow-sm">
          <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Comparison Evaluation Error</p>
            <p className="text-xs text-rose-700 mt-0.5">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Optional Audited Factors Drawer */}
      {showRegistry && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-emerald-600" />
              <h3 className="text-sm font-bold text-slate-900">Audited Emission Factors Registry (India GHG Program & CEA)</h3>
            </div>
            <span className="text-xs text-slate-400">Strict Tailpipe CO₂ Only</span>
          </div>

          {isLoadingFactors ? (
            <div className="py-6 text-center text-xs text-slate-400">Loading audited factors...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {factors.map((f) => (
                <div key={f.factor_id} className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1">
                  <div className="flex justify-between font-bold text-slate-800">
                    <span>{f.mode.replace(/_/g, ' ')}</span>
                    <span className="text-emerald-700">{f.default_value} {f.unit}</span>
                  </div>
                  <p className="text-[11px] text-slate-500">{f.source_name} ({f.publication_year})</p>
                  <p className="text-[10px] text-slate-400 truncate">{f.limitations}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Form & Results Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Form (1 col) */}
        <div className="lg:col-span-1 bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-5">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Car className="w-5 h-5 text-emerald-600" />
            <h2 className="text-base font-bold text-slate-900">Commute Parameters</h2>
          </div>

          <form onSubmit={handleCompareSubmit} className="space-y-4 text-xs">
            {/* Station Selector */}
            <div>
              <label htmlFor="transport-station" className="block font-semibold text-slate-700 mb-1">
                Ambient Monitoring Station (AQI Context) *
              </label>
              <select
                id="transport-station"
                value={stationId}
                onChange={(e) => setStationId(e.target.value)}
                required
                className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
              >
                {stations.map((s) => (
                  <option key={s.station_id} value={s.station_id}>
                    {s.station_name} ({s.city})
                  </option>
                ))}
              </select>
            </div>

            {/* Current Transport Mode */}
            <div>
              <label htmlFor="current-mode" className="block font-semibold text-slate-700 mb-1">
                Current Baseline Mode
              </label>
              <select
                id="current-mode"
                value={currentMode}
                onChange={(e) => setCurrentMode(e.target.value as TransportMode)}
                className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
              >
                <option value="petrol_car">Private Petrol Car</option>
                <option value="diesel_car">Private Diesel Car</option>
                <option value="petrol_motorcycle">Two-Wheeler (Petrol)</option>
                <option value="cng_auto">CNG Auto-Rickshaw</option>
                <option value="intracity_bus">Intracity Public Bus</option>
                <option value="carpool">Shared Carpool</option>
                <option value="metro">Metro Rail</option>
                <option value="electric_vehicle">Electric Car (EV)</option>
                <option value="walking">Walking</option>
                <option value="cycling">Cycling</option>
              </select>
            </div>

            {/* Fuel Type when Car is selected */}
            {(currentMode === 'petrol_car' || currentMode === 'diesel_car') && (
              <div>
                <label htmlFor="fuel-type" className="block font-semibold text-slate-700 mb-1">
                  Fuel Type
                </label>
                <select
                  id="fuel-type"
                  value={fuelType}
                  onChange={(e) => setFuelType(e.target.value as FuelType)}
                  className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                >
                  <option value="petrol">Petrol (BS VI)</option>
                  <option value="diesel">Diesel (BS VI)</option>
                  <option value="cng">Compressed Natural Gas (CNG)</option>
                </select>
              </div>
            )}

            {/* Distance & Round-Trip */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="trip-distance" className="block font-semibold text-slate-700 mb-1">
                  Trip Distance (km)
                </label>
                <input
                  id="trip-distance"
                  type="number"
                  step="0.5"
                  min="0.5"
                  max="150"
                  value={distanceKm}
                  onChange={(e) => setDistanceKm(parseFloat(e.target.value) || 0)}
                  required
                  className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                />
              </div>

              <div>
                <label htmlFor="vehicle-occupancy" className="block font-semibold text-slate-700 mb-1">
                  Occupancy
                </label>
                <input
                  id="vehicle-occupancy"
                  type="number"
                  min="1"
                  max={currentMode === 'cng_auto' ? 3 : 9}
                  value={occupancy}
                  onChange={(e) => setOccupancy(parseInt(e.target.value, 10) || 1)}
                  className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                />
              </div>
            </div>

            {/* Round trip toggle & weekly trips */}
            <div className="grid grid-cols-2 gap-3">
              <label className="flex items-center gap-2 p-2 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={roundTrip}
                  onChange={(e) => setRoundTrip(e.target.checked)}
                  className="rounded text-emerald-600 focus:ring-emerald-500"
                />
                <span className="text-[11px] font-semibold text-slate-700">Round-Trip Daily</span>
              </label>

              <div>
                <label htmlFor="trips-week" className="block font-semibold text-slate-700 mb-0.5">
                  Trips / Week
                </label>
                <input
                  id="trips-week"
                  type="number"
                  min="1"
                  max="14"
                  value={tripsPerWeek}
                  onChange={(e) => setTripsPerWeek(parseInt(e.target.value, 10) || 5)}
                  className="w-full px-2 py-1 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                />
              </div>
            </div>

            {/* Alternative Modes Selector */}
            <div className="pt-2 border-t border-slate-100 space-y-2">
              <span className="block font-semibold text-slate-700">
                Alternative Modes to Evaluate ({selectedAlternatives.length} selected)
              </span>

              {[
                { mode: 'metro' as TransportMode, label: 'Delhi Metro / Rail' },
                { mode: 'intracity_bus' as TransportMode, label: 'Public Bus' },
                { mode: 'carpool' as TransportMode, label: 'Carpooling (Shared)' },
                { mode: 'electric_vehicle' as TransportMode, label: 'Electric Vehicle (EV)' },
                { mode: 'cng_auto' as TransportMode, label: 'CNG Auto-Rickshaw' },
                { mode: 'cycling' as TransportMode, label: 'Cycling (Active)' },
                { mode: 'walking' as TransportMode, label: 'Walking (Active)' },
              ].map(({ mode, label }) => (
                <label key={mode} className="flex items-center justify-between p-2 rounded-lg border border-slate-100 hover:bg-slate-50 cursor-pointer">
                  <span className="text-slate-700">{label}</span>
                  <input
                    type="checkbox"
                    checked={selectedAlternatives.includes(mode)}
                    onChange={() => handleToggleAlternative(mode)}
                    className="rounded text-emerald-600 focus:ring-emerald-500"
                  />
                </label>
              ))}
            </div>

            <button
              type="submit"
              disabled={isSubmitting || !stationId}
              className="w-full mt-3 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow-sm hover:shadow transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Calculating Tailpipe Factors...
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  Compare Commute Emissions
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Comparison Results (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          {comparisonResult ? (
            <>
              {/* Baseline Summary Card */}
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pb-3 border-b border-slate-100">
                  <div>
                    <span className="text-xs uppercase font-bold text-slate-400">Baseline Commute Profile</span>
                    <h3 className="text-lg font-bold text-slate-900 mt-0.5 capitalize">
                      {comparisonResult.baseline_result.mode.replace(/_/g, ' ')}
                    </h3>
                    <p className="text-xs text-slate-500">
                      Evaluated: {comparisonResult.effective_distance_km} km ({comparisonResult.round_trip ? 'Round Trip' : 'One Way'}) • Occupancy: {comparisonResult.baseline_result.occupancy}
                    </p>
                  </div>

                  <div className="text-right">
                    <span className="text-xs text-slate-400">Passenger Tailpipe CO₂</span>
                    <div className="text-xl font-black text-rose-600 mt-0.5">
                      {comparisonResult.baseline_result.passenger_emissions_kg_co2?.toFixed(3) || '0.000'} kg
                    </div>
                  </div>
                </div>

                {/* AQI & Health Advisory Integration */}
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-800">
                      Ambient Condition at {comparisonResult.station_name}:
                    </span>
                    <span 
                      className="px-2 py-0.5 rounded text-xs font-bold"
                      style={{ backgroundColor: aqiBand.bgHex, color: aqiBand.textHex }}
                    >
                      AQI {comparisonResult.current_aqi || '401+'} ({comparisonResult.aqi_category})
                    </span>
                  </div>
                  <p className="text-slate-600 leading-relaxed">
                    <strong>NCDC Transit Advisory:</strong> {comparisonResult.ncdc_general_advisory}
                  </p>
                </div>
              </div>

              {/* Alternatives Comparison Grid */}
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ArrowRight className="w-5 h-5 text-emerald-600" />
                    <h3 className="text-base font-bold text-slate-900">Evaluated Alternatives & Avoided CO₂</h3>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">Tailpipe CO₂ Only</span>
                </div>

                <div className="space-y-3">
                  {comparisonResult.avoided_comparisons.map((comp, idx) => {
                    const altResult = comparisonResult.alternative_results.find(
                      (r) => r.mode === comp.alternative_mode
                    );
                    const isReduction = (comp.avoided_kg_co2_per_trip || 0) > 0;

                    return (
                      <div
                        key={idx}
                        className="p-4 rounded-xl bg-slate-50 border border-slate-200 hover:border-slate-300 transition space-y-2"
                      >
                        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-slate-900 capitalize">
                              {comp.alternative_mode.replace(/_/g, ' ')}
                            </span>
                            {altResult?.is_recommended_for_commute ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 flex items-center gap-1">
                                <CheckCircle className="w-3 h-3" /> Recommended
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 flex items-center gap-1">
                                <AlertTriangle className="w-3 h-3" /> High Smog Exposure
                              </span>
                            )}
                          </div>

                          <div className="text-right">
                            <span className={`text-sm font-black ${isReduction ? 'text-emerald-700' : 'text-slate-600'}`}>
                              {isReduction
                                ? `Avoids ${comp.avoided_kg_co2_per_trip?.toFixed(3)} kg CO₂`
                                : `Emits ${altResult?.passenger_emissions_kg_co2?.toFixed(3)} kg CO₂`}
                            </span>
                            <span className="text-[11px] text-slate-400 block">per trip</span>
                          </div>
                        </div>

                        {/* Projection */}
                        <div className="flex flex-wrap gap-3 text-xs text-slate-600 pt-1 border-t border-slate-200/60">
                          <span>
                            Weekly Saving:{' '}
                            <strong className="text-slate-900">
                              {comp.projected_weekly_saving_kg_co2?.toFixed(2) || '0.00'} kg
                            </strong>
                          </span>
                          <span>
                            Monthly Projection:{' '}
                            <strong className="text-slate-900">
                              {comp.projected_monthly_saving_kg_co2?.toFixed(2) || '0.00'} kg
                            </strong>
                          </span>
                        </div>

                        {/* Health Advisory Note */}
                        {altResult?.health_guidance_note && (
                          <p className="text-[11px] text-amber-900 bg-amber-50 p-2 rounded border border-amber-100">
                            <strong>Exposure Guidance: </strong>
                            {altResult.health_guidance_note}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>

                {onNavigateToImpact && (
                  <div className="pt-3 border-t border-slate-100 flex justify-end">
                    <button
                      onClick={onNavigateToImpact}
                      className="px-4 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-xs font-semibold rounded-lg border border-emerald-200 transition flex items-center gap-1.5"
                    >
                      Log Completed Trips in Impact Tracker <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>

              {/* Methodology Limitations Card */}
              <div className="bg-slate-50 rounded-xl border border-slate-200 p-4 text-xs text-slate-500 space-y-1">
                <span className="font-bold text-slate-700">Non-Invention & Scope Disclaimers:</span>
                <p>• All values represent direct operational tailpipe CO₂ only (not lifecycle CO₂e).</p>
                <p>• Metro emissions exclude station HVAC/lighting per CEA official boundary rules.</p>
                <p>• EV emissions apply India grid average factor without hypothetical solar charging claims.</p>
              </div>
            </>
          ) : (
            /* Empty State */
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center space-y-4">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-50 text-emerald-600">
                <Leaf className="w-8 h-8" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h3 className="text-lg font-bold text-slate-900">Awaiting Commute Configuration</h3>
                <p className="text-xs text-slate-500">
                  Select your current baseline vehicle and alternative modes to evaluate tailpipe carbon savings and in-transit exposure warnings.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

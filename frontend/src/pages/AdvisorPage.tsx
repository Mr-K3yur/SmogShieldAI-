import React, { useState, useEffect } from 'react';
import {
  Home,
  Wind,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  ShieldCheck,
  RefreshCw,
  Flame,
  Info
} from 'lucide-react';
import {
  CADRUnit,
  HouseholdBudget,
  IndoorAssessmentRequest,
  IndoorAssessmentResponse,
  StationMetadata,
} from '../types';
import { aqiApi, advisorApi } from '../services/api';

interface AdvisorPageProps {
  selectedStationId?: string;
}

export const AdvisorPage: React.FC<AdvisorPageProps> = ({ selectedStationId }) => {
  // Station context
  const [stations, setStations] = useState<StationMetadata[]>([]);
  const [stationId, setStationId] = useState<string>(selectedStationId || '');

  // Room geometry & purifier inputs
  const [roomLength, setRoomLength] = useState<number>(5.0);
  const [roomWidth, setRoomWidth] = useState<number>(4.0);
  const [ceilingHeight, setCeilingHeight] = useState<number>(3.0);
  const [unitMode, setUnitMode] = useState<'meters' | 'feet'>('meters');

  const [hasPurifier, setHasPurifier] = useState<boolean>(true);
  const [cadrValue, setCadrValue] = useState<number>(300);
  const [cadrUnit, setCadrUnit] = useState<CADRUnit>('m3/h');
  const [smokeCadr, setSmokeCadr] = useState<string>('');
  const [filterType, setFilterType] = useState<string>('HEPA H13');

  // Behavioral & Environmental sources
  const [hasAgarbatti, setHasAgarbatti] = useState<boolean>(false);
  const [hasMosquitoCoil, setHasMosquitoCoil] = useState<boolean>(false);
  const [hasUnventedCooking, setHasUnventedCooking] = useState<boolean>(false);
  const [hasSmoking, setHasSmoking] = useState<boolean>(false);
  const [ventilationAvailable, setVentilationAvailable] = useState<boolean>(true);
  const [householdBudget, setHouseholdBudget] = useState<HouseholdBudget>('medium');
  const [targetAch, setTargetAch] = useState<string>('');

  // Assessment results
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [assessmentResult, setAssessmentResult] = useState<IndoorAssessmentResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load stations on mount for outdoor context
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
        // Optional outdoor context
      }
    }
    loadStations();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleAssessmentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    // Geometry normalization to metres
    const factor = unitMode === 'feet' ? 0.3048 : 1.0;
    const lMeters = Number((roomLength * factor).toFixed(2));
    const wMeters = Number((roomWidth * factor).toFixed(2));
    const hMeters = Number((ceilingHeight * factor).toFixed(2));

    const sources: string[] = [];
    if (hasAgarbatti) sources.push('incense_agarbatti');
    if (hasMosquitoCoil) sources.push('mosquito_coils');
    if (hasUnventedCooking) sources.push('unvented_cooking');
    if (hasSmoking) sources.push('tobacco_smoke');

    const payload: IndoorAssessmentRequest = {
      station_id: stationId ? stationId : null,
      room_length_m: lMeters,
      room_width_m: wMeters,
      ceiling_height_m: hMeters,
      has_air_purifier: hasPurifier,
      cadr: hasPurifier && cadrValue > 0 ? cadrValue : null,
      smoke_cadr: hasPurifier && smokeCadr.trim() && parseFloat(smokeCadr) > 0 ? parseFloat(smokeCadr) : null,
      cadr_unit: cadrUnit,
      filter_type: hasPurifier ? filterType : null,
      indoor_pollution_sources: sources,
      ventilation_available: ventilationAvailable,
      household_budget: householdBudget,
      target_ach: targetAch.trim() && parseFloat(targetAch) > 0 ? parseFloat(targetAch) : null,
    };

    try {
      const response = await advisorApi.assessIndoor(payload);
      setAssessmentResult(response);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to evaluate indoor air assessment.';
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 mb-2">
            <Home className="w-3.5 h-3.5" />
            Physical CADR & Source Control Engine
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Indoor Air & Filtration Advisor</h1>
          <p className="text-sm text-slate-500 mt-1">
            Physical room volume calculations, CADR-to-ACH mechanical sizing, and prioritized source control mitigations.
          </p>
        </div>
      </div>

      {/* Error alert */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start gap-3 shadow-sm">
          <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Calculation Error</p>
            <p className="text-xs text-rose-700 mt-0.5">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Main Form and Output Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form Controls (1 col) */}
        <div className="lg:col-span-1 bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Wind className="w-5 h-5 text-indigo-600" />
              <h2 className="text-base font-bold text-slate-900">Room & Filtration Inputs</h2>
            </div>

            {/* Units Toggle */}
            <div className="inline-flex rounded-lg border border-slate-200 p-0.5 text-xs bg-slate-50">
              <button
                type="button"
                onClick={() => setUnitMode('meters')}
                className={`px-2 py-0.5 rounded font-medium ${unitMode === 'meters' ? 'bg-white shadow-xs text-indigo-700 font-bold' : 'text-slate-500'}`}
              >
                Metres
              </button>
              <button
                type="button"
                onClick={() => setUnitMode('feet')}
                className={`px-2 py-0.5 rounded font-medium ${unitMode === 'feet' ? 'bg-white shadow-xs text-indigo-700 font-bold' : 'text-slate-500'}`}
              >
                Feet
              </button>
            </div>
          </div>

          <form onSubmit={handleAssessmentSubmit} className="space-y-4 text-xs">
            {/* Dimensions */}
            <div>
              <span className="block font-semibold text-slate-700 mb-2">
                Room Dimensions ({unitMode === 'meters' ? 'metres' : 'feet'})
              </span>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label htmlFor="room-length" className="text-[11px] text-slate-500 block mb-0.5">Length</label>
                  <input
                    id="room-length"
                    type="number"
                    step="0.1"
                    min="1"
                    max="50"
                    value={roomLength}
                    onChange={(e) => setRoomLength(parseFloat(e.target.value) || 0)}
                    required
                    className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                  />
                </div>
                <div>
                  <label htmlFor="room-width" className="text-[11px] text-slate-500 block mb-0.5">Width</label>
                  <input
                    id="room-width"
                    type="number"
                    step="0.1"
                    min="1"
                    max="50"
                    value={roomWidth}
                    onChange={(e) => setRoomWidth(parseFloat(e.target.value) || 0)}
                    required
                    className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                  />
                </div>
                <div>
                  <label htmlFor="room-height" className="text-[11px] text-slate-500 block mb-0.5">Ceiling Height</label>
                  <input
                    id="room-height"
                    type="number"
                    step="0.1"
                    min="1"
                    max="15"
                    value={ceilingHeight}
                    onChange={(e) => setCeilingHeight(parseFloat(e.target.value) || 0)}
                    required
                    className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                  />
                </div>
              </div>
            </div>

            {/* Air Purifier Toggle */}
            <div className="pt-2 border-t border-slate-100">
              <label className="flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer">
                <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                  <Wind className="w-4 h-4 text-indigo-600" /> Air Purifier Present
                </span>
                <input
                  type="checkbox"
                  checked={hasPurifier}
                  onChange={(e) => setHasPurifier(e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                />
              </label>
            </div>

            {/* Purifier Details */}
            {hasPurifier && (
              <div className="space-y-3 p-3 bg-indigo-50/40 rounded-xl border border-indigo-100">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label htmlFor="cadr-input" className="block text-[11px] font-semibold text-slate-700 mb-0.5">
                      CADR Rating
                    </label>
                    <input
                      id="cadr-input"
                      type="number"
                      min="0"
                      max="2000"
                      value={cadrValue}
                      onChange={(e) => setCadrValue(parseFloat(e.target.value) || 0)}
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-800"
                    />
                  </div>
                  <div>
                    <label htmlFor="cadr-unit" className="block text-[11px] font-semibold text-slate-700 mb-0.5">
                      CADR Unit
                    </label>
                    <select
                      id="cadr-unit"
                      value={cadrUnit}
                      onChange={(e) => setCadrUnit(e.target.value as CADRUnit)}
                      className="w-full px-2 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-800"
                    >
                      <option value="m3/h">m³/hour</option>
                      <option value="CFM">CFM (Cubic Ft/Min)</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label htmlFor="filter-type" className="block text-[11px] font-semibold text-slate-700 mb-0.5">
                    Filter Type (Self-Reported)
                  </label>
                  <select
                    id="filter-type"
                    value={filterType}
                    onChange={(e) => setFilterType(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-800"
                  >
                    <option value="HEPA H13">True HEPA (H13 / 99.97%)</option>
                    <option value="HEPA H11 / EPA">EPA / Semi-HEPA (H11)</option>
                    <option value="Activated Carbon Composite">HEPA + Activated Carbon</option>
                    <option value="MERV 13 (DIY Box)">MERV 13 (Corsi-Rosenthal Box)</option>
                    <option value="Basic Pre-Filter Only">Basic Mesh / Pre-Filter Only</option>
                    <option value="Unknown">Unknown / Generic</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="smoke-cadr-input" className="block text-[11px] font-semibold text-slate-700 mb-0.5">
                    Smoke CADR (Fine Particulate / PM2.5) Optional
                  </label>
                  <input
                    id="smoke-cadr-input"
                    type="number"
                    min="0"
                    max="2000"
                    placeholder="e.g. 280 (leave blank if unknown)"
                    value={smokeCadr}
                    onChange={(e) => setSmokeCadr(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-800"
                  />
                </div>

                <div>
                  <label htmlFor="target-ach" className="block text-[11px] font-semibold text-slate-700 mb-0.5">
                    Optional Target ACH Sizing
                  </label>
                  <input
                    id="target-ach"
                    type="number"
                    step="0.5"
                    min="1"
                    max="12"
                    placeholder="e.g. 4.0 or 5.0"
                    value={targetAch}
                    onChange={(e) => setTargetAch(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-800"
                  />
                  <span className="text-[10px] text-slate-500 mt-0.5 block">
                    Calculates required CADR to reach this target. (Never automatically enforced).
                  </span>
                </div>
              </div>
            )}

            {/* Indoor Particulate Sources */}
            <div className="pt-2 border-t border-slate-100 space-y-2">
              <span className="block font-semibold text-slate-700">Indoor Combustion & Aerosol Sources</span>
              
              <label className="flex items-center justify-between p-2 rounded-lg border border-slate-100 hover:bg-slate-50 cursor-pointer">
                <span className="flex items-center gap-1.5 text-slate-700">
                  <Flame className="w-3.5 h-3.5 text-amber-500" /> Incense / Agarbatti / Dhoop
                </span>
                <input
                  type="checkbox"
                  checked={hasAgarbatti}
                  onChange={(e) => setHasAgarbatti(e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-indigo-500"
                />
              </label>

              <label className="flex items-center justify-between p-2 rounded-lg border border-slate-100 hover:bg-slate-50 cursor-pointer">
                <span className="flex items-center gap-1.5 text-slate-700">
                  <Flame className="w-3.5 h-3.5 text-rose-500" /> Mosquito Coils
                </span>
                <input
                  type="checkbox"
                  checked={hasMosquitoCoil}
                  onChange={(e) => setHasMosquitoCoil(e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-indigo-500"
                />
              </label>

              <label className="flex items-center justify-between p-2 rounded-lg border border-slate-100 hover:bg-slate-50 cursor-pointer">
                <span className="flex items-center gap-1.5 text-slate-700">
                  <Flame className="w-3.5 h-3.5 text-orange-500" /> Unvented Cooking / Chulha
                </span>
                <input
                  type="checkbox"
                  checked={hasUnventedCooking}
                  onChange={(e) => setHasUnventedCooking(e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-indigo-500"
                />
              </label>

              <label className="flex items-center justify-between p-2 rounded-lg border border-slate-100 hover:bg-slate-50 cursor-pointer">
                <span className="flex items-center gap-1.5 text-slate-700">
                  <Flame className="w-3.5 h-3.5 text-red-600" /> Tobacco Smoking
                </span>
                <input
                  type="checkbox"
                  checked={hasSmoking}
                  onChange={(e) => setHasSmoking(e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-indigo-500"
                />
              </label>
            </div>

            {/* Ventilation Available Toggle */}
            <div className="pt-2 border-t border-slate-100">
              <label className="flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer">
                <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                  <Wind className="w-4 h-4 text-blue-600" /> Operable Windows / Ventilation Vents
                </span>
                <input
                  type="checkbox"
                  checked={ventilationAvailable}
                  onChange={(e) => setVentilationAvailable(e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                />
              </label>
            </div>

            {/* Outdoor context selector */}
            <div className="pt-2 border-t border-slate-100">
              <label htmlFor="advisor-station" className="block text-[11px] font-semibold text-slate-700 mb-0.5">
                Outdoor Monitoring Station (Context)
              </label>
              <select
                id="advisor-station"
                value={stationId}
                onChange={(e) => setStationId(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
              >
                <option value="">None (Indoor Physics Only)</option>
                {stations.map((s) => (
                  <option key={s.station_id} value={s.station_id}>
                    {s.station_name} ({s.city})
                  </option>
                ))}
              </select>
            </div>

            {/* Household Budget */}
            <div>
              <label htmlFor="advisor-budget" className="block text-[11px] font-semibold text-slate-700 mb-0.5">
                Budget Priority
              </label>
              <select
                id="advisor-budget"
                value={householdBudget}
                onChange={(e) => setHouseholdBudget(e.target.value as HouseholdBudget)}
                className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
              >
                <option value="low">Low (DIY & Non-Electric Focus)</option>
                <option value="medium">Medium (Standard Mechanical Filter)</option>
                <option value="high">High (Maximum Sealed Sizing)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-3 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm hover:shadow transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Calculating Sizing & ACH...
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  Assess Room & Purifier
                </>
              )}
            </button>
          </form>
        </div>

        {/* Results Presentation (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          {assessmentResult ? (
            <>
              {/* Sizing & Metrics Overview */}
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pb-3 border-b border-slate-100">
                  <div>
                    <span className="text-xs uppercase font-bold text-slate-400">Physical Sizing Evaluation</span>
                    <h3 className="text-lg font-bold text-slate-900 mt-0.5">
                      Room Volume: {assessmentResult.room_volume_m3.toFixed(1)} m³
                    </h3>
                  </div>

                  <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                    assessmentResult.calculated_ach && assessmentResult.calculated_ach >= 3
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : 'bg-amber-50 text-amber-700 border border-amber-200'
                  }`}>
                    {assessmentResult.filtration_assessment.purifier_status}
                  </span>
                </div>

                {/* Sizing Metrics Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                    <span className="text-[11px] text-slate-500 block">Room Volume</span>
                    <span className="text-base font-extrabold text-slate-900 mt-1 block">
                      {assessmentResult.room_volume_m3.toFixed(1)} m³
                    </span>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                    <span className="text-[11px] text-slate-500 block">Available CADR</span>
                    <span className="text-base font-extrabold text-indigo-700 mt-1 block">
                      {assessmentResult.available_cadr_m3h ? `${assessmentResult.available_cadr_m3h} m³/h` : '--'}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {assessmentResult.available_cadr_cfm ? `(${assessmentResult.available_cadr_cfm} CFM)` : ''}
                    </span>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                    <span className="text-[11px] text-slate-500 block">Estimated ACH</span>
                    <span className="text-base font-extrabold text-slate-900 mt-1 block">
                      {assessmentResult.calculated_ach !== null && assessmentResult.calculated_ach !== undefined
                        ? `${assessmentResult.calculated_ach.toFixed(1)} ACH`
                        : '--'}
                    </span>
                    <span className="text-[10px] text-slate-400">Air Changes / Hour</span>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                    <span className="text-[11px] text-slate-500 block">Target Sizing</span>
                    <span className="text-base font-extrabold text-blue-700 mt-1 block">
                      {assessmentResult.required_cadr_m3h
                        ? `${assessmentResult.required_cadr_m3h} m³/h`
                        : 'Unspecified'}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {assessmentResult.target_ach ? `for ${assessmentResult.target_ach} ACH` : 'No target set'}
                    </span>
                  </div>
                </div>

                {/* Filtration Assessment Explanation */}
                <div className="p-3.5 bg-indigo-50/50 rounded-xl border border-indigo-100 text-xs text-slate-700 space-y-2">
                  <div className="flex items-center gap-1.5 font-bold text-indigo-900">
                    <ShieldCheck className="w-4 h-4 text-indigo-600" />
                    <span>Technical Filtration Sizing</span>
                  </div>
                  <p className="leading-relaxed">{assessmentResult.filtration_assessment.explanation}</p>
                  
                  {assessmentResult.filtration_assessment.target_comparison && (
                    <p className="font-semibold text-indigo-950 mt-1">
                      {assessmentResult.filtration_assessment.target_comparison}
                    </p>
                  )}

                  {assessmentResult.filtration_assessment.guidance && assessmentResult.filtration_assessment.guidance.length > 0 && (
                    <ul className="mt-2 space-y-1">
                      {assessmentResult.filtration_assessment.guidance.map((g, gIdx) => (
                        <li key={gIdx} className="text-[11px] text-indigo-900 flex items-start gap-1">
                          • <span>{g}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              {/* Source Control Recommendations */}
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  <h3 className="text-base font-bold text-slate-900">Prioritized Indoor Source Control</h3>
                </div>

                <div className="space-y-2.5">
                  {assessmentResult.source_control_recommendations.map((item, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 text-xs"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            item.priority === 'HIGH' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'
                          }`}>
                            {item.priority}
                          </span>
                          <span className="font-bold text-slate-900">{item.action}</span>
                        </div>
                        <p className="text-slate-600 mt-1">{item.reason}</p>
                      </div>
                      <span className="text-[11px] font-medium text-slate-500 whitespace-nowrap bg-white px-2 py-1 rounded border border-slate-200">
                        Source: {item.source}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Ventilation Strategy */}
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Wind className="w-5 h-5 text-blue-600" />
                    <h3 className="text-base font-bold text-slate-900">Condition-Based Ventilation Strategy</h3>
                  </div>
                  {assessmentResult.ventilation_recommendations.outdoor_aqi_category && (
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                      Outdoor: {assessmentResult.ventilation_recommendations.outdoor_aqi_category}
                    </span>
                  )}
                </div>

                <div className="p-3 rounded-lg bg-blue-50/50 border border-blue-100 text-xs space-y-1.5">
                  <span className="font-bold text-blue-950">
                    Strategy: {assessmentResult.ventilation_recommendations.strategy}
                  </span>
                  <p className="text-slate-700 leading-relaxed">
                    {assessmentResult.ventilation_recommendations.guidance}
                  </p>
                </div>

                {assessmentResult.ventilation_recommendations.precautions.length > 0 && (
                  <div className="space-y-1 text-xs">
                    <span className="font-semibold text-slate-700">Safety Precautions:</span>
                    <ul className="space-y-1">
                      {assessmentResult.ventilation_recommendations.precautions.map((p, pIdx) => (
                        <li key={pIdx} className="text-slate-600 flex items-start gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
                          <span>{p}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Warnings & Plant Myths */}
              <div className="bg-amber-50/60 rounded-xl border border-amber-200 p-4 text-xs text-amber-900 space-y-2">
                <div className="flex items-center gap-1.5 font-bold">
                  <Info className="w-4 h-4 text-amber-700" />
                  <span>Physics Constraints & Scientific Integrity</span>
                </div>
                <div className="space-y-1 text-[11px] text-amber-800">
                  <p>• <strong>Houseplant Reality:</strong> Potted indoor plants cannot substitute for mechanical CADR filtration for toxic PM2.5.</p>
                  <p>• <strong>No Ozone Risk:</strong> Avoid electrostatic or ionizer purifiers emitting unconstrained ozone.</p>
                  <p>• <strong>Gas Appliance Backdraft:</strong> Ensure high-volume kitchen exhaust fans do not depressurize flues when running gas water heaters.</p>
                </div>
              </div>
            </>
          ) : (
            /* Empty State */
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center space-y-4">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-indigo-50 text-indigo-600">
                <Wind className="w-8 h-8" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h3 className="text-lg font-bold text-slate-900">Awaiting Room Parameters</h3>
                <p className="text-xs text-slate-500">
                  Enter your room dimensions and air purifier specifications to calculate theoretical CADR, estimated Air Changes per Hour (ACH), and condition-based ventilation advice.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

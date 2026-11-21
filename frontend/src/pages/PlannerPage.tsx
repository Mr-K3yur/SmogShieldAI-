import React, { useState, useEffect } from 'react';
import {
  CalendarClock,
  ShieldAlert,
  Users,
  Compass,
  CheckCircle,
  AlertTriangle,
  Clock,
  GraduationCap,
  Sparkles,
  ExternalLink,
  ChevronRight,
  RefreshCw
} from 'lucide-react';
import {
  StationMetadata,
  HouseholdBudget,
  CommuteMethod,
  DailyPlannerRequest,
  DailyPlannerResponse,
} from '../types';
import { aqiApi, plannerApi } from '../services/api';
import { getBandForCategory } from '../utils/cpcbColors';

interface PlannerPageProps {
  selectedStationId?: string;
}

export const PlannerPage: React.FC<PlannerPageProps> = ({ selectedStationId }) => {
  // Station listing state
  const [stations, setStations] = useState<StationMetadata[]>([]);
  const [isLoadingStations, setIsLoadingStations] = useState<boolean>(true);

  // Form input state
  const [stationId, setStationId] = useState<string>(selectedStationId || '');
  const [familySize, setFamilySize] = useState<number>(4);
  const [hasChildren, setHasChildren] = useState<boolean>(true);
  const [hasOlderAdults, setHasOlderAdults] = useState<boolean>(false);
  const [hasSensitiveMember, setHasSensitiveMember] = useState<boolean>(false);
  const [householdBudget, setHouseholdBudget] = useState<HouseholdBudget>('medium');
  const [commuteMethod, setCommuteMethod] = useState<CommuteMethod>('metro');
  const [schoolSchedule, setSchoolSchedule] = useState<string>('07:30 - 13:30');
  const [workSchedule, setWorkSchedule] = useState<string>('09:00 - 18:00');
  const [preferredLanguage, setPreferredLanguage] = useState<string>('en');

  // Plan generation state
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [planResult, setPlanResult] = useState<DailyPlannerResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // 1. Load stations on mount
  useEffect(() => {
    let isMounted = true;
    async function loadStations() {
      setIsLoadingStations(true);
      try {
        let res = await aqiApi.listStations();
        if (res.stations.length === 0) {
          res = await aqiApi.listStations({ provider: 'mock' });
        }
        if (isMounted) {
          const list = res.stations || [];
          setStations(list);
          if (list.length > 0 && !stationId) {
            setStationId(list[0].station_id);
          }
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : 'Failed to discover stations.';
          setErrorMessage(msg);
        }
      } finally {
        if (isMounted) setIsLoadingStations(false);
      }
    }
    loadStations();
    return () => {
      isMounted = false;
    };
  }, []);

  // Update station if passed from parent
  useEffect(() => {
    if (selectedStationId) {
      setStationId(selectedStationId);
    }
  }, [selectedStationId]);

  // 2. Handle Plan Generation
  const handleGeneratePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stationId) {
      setErrorMessage('Please select a monitoring station for local air quality context.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    const payload: DailyPlannerRequest = {
      station_id: stationId,
      family_size: familySize,
      has_children: hasChildren,
      has_older_adults: hasOlderAdults,
      has_sensitive_member: hasSensitiveMember,
      household_budget: householdBudget,
      commute_method: commuteMethod,
      school_schedule: hasChildren && schoolSchedule.trim() ? schoolSchedule.trim() : null,
      work_schedule: workSchedule.trim() ? workSchedule.trim() : null,
      preferred_language: preferredLanguage,
    };

    try {
      const response = await plannerApi.generate(payload);
      setPlanResult(response);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate personalized daily planner.';
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const aqiBand = getBandForCategory(planResult?.aqi_context.category);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 mb-2">
            <CalendarClock className="w-3.5 h-3.5" />
            NCDC 2025 Advisory Engine
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Personalized Daily Activity Planner</h1>
          <p className="text-sm text-slate-500 mt-1">
            Condition-based daily scheduling, commute safety, and school recess adaptation aligned with official MoHFW guidelines.
          </p>
        </div>
      </div>

      {/* Error alert */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start gap-3 shadow-sm">
          <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Planner Calculation Error</p>
            <p className="text-xs text-rose-700 mt-0.5">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Input Form & Configuration Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Form Controls (2 cols on large screen) */}
        <div className="lg:col-span-1 bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-5">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Users className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-bold text-slate-900">Household Profile & Commute</h2>
          </div>

          <form onSubmit={handleGeneratePlan} className="space-y-4">
            {/* Station Selector */}
            <div>
              <label htmlFor="planner-station" className="block text-xs font-semibold text-slate-700 mb-1">
                Ambient Monitoring Station *
              </label>
              <select
                id="planner-station"
                value={stationId}
                onChange={(e) => setStationId(e.target.value)}
                disabled={isLoadingStations}
                required
                className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {isLoadingStations ? (
                  <option value="">Discovering stations...</option>
                ) : stations.length === 0 ? (
                  <option value="">No stations available</option>
                ) : (
                  stations.map((s) => (
                    <option key={s.station_id} value={s.station_id}>
                      {s.station_name} ({s.city})
                    </option>
                  ))
                )}
              </select>
            </div>

            {/* Family Size */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label htmlFor="family-size" className="text-xs font-semibold text-slate-700">
                  Family Members in Household
                </label>
                <span className="text-xs font-bold text-blue-600 font-mono">{familySize} persons</span>
              </div>
              <input
                id="family-size"
                type="range"
                min="1"
                max="15"
                value={familySize}
                onChange={(e) => setFamilySize(parseInt(e.target.value, 10))}
                className="w-full accent-blue-600"
              />
            </div>

            {/* Demographic Toggles */}
            <div className="space-y-2 pt-1">
              <span className="block text-xs font-semibold text-slate-700">Demographic Vulnerabilities</span>

              <label className="flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer text-xs">
                <span className="flex items-center gap-2 text-slate-700 font-medium">
                  <GraduationCap className="w-4 h-4 text-blue-500" /> School-Age Children
                </span>
                <input
                  type="checkbox"
                  checked={hasChildren}
                  onChange={(e) => setHasChildren(e.target.checked)}
                  className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4"
                />
              </label>

              <label className="flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer text-xs">
                <span className="flex items-center gap-2 text-slate-700 font-medium">
                  <Users className="w-4 h-4 text-amber-500" /> Older Adults (60+)
                </span>
                <input
                  type="checkbox"
                  checked={hasOlderAdults}
                  onChange={(e) => setHasOlderAdults(e.target.checked)}
                  className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4"
                />
              </label>

              <label className="flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer text-xs">
                <span className="flex items-center gap-2 text-slate-700 font-medium">
                  <ShieldAlert className="w-4 h-4 text-rose-500" /> Respiratory / Cardiac History
                </span>
                <input
                  type="checkbox"
                  checked={hasSensitiveMember}
                  onChange={(e) => setHasSensitiveMember(e.target.checked)}
                  className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4"
                />
              </label>
            </div>

            {/* Commute Method & Budget */}
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <label htmlFor="commute-mode" className="block text-xs font-semibold text-slate-700 mb-1">
                  Primary Commute
                </label>
                <select
                  id="commute-mode"
                  value={commuteMethod}
                  onChange={(e) => setCommuteMethod(e.target.value as CommuteMethod)}
                  className="w-full px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                >
                  <option value="metro">Metro Rail</option>
                  <option value="bus">Public Bus</option>
                  <option value="car_ac">Car (Enclosed AC)</option>
                  <option value="car_non_ac">Car (Non-AC)</option>
                  <option value="carpool">Carpooling</option>
                  <option value="auto_rickshaw">Auto-Rickshaw</option>
                  <option value="two_wheeler">Two-Wheeler</option>
                  <option value="walk">Walking</option>
                  <option value="bicycle">Bicycle</option>
                  <option value="work_from_home">Work From Home</option>
                </select>
              </div>

              <div>
                <label htmlFor="household-budget" className="block text-xs font-semibold text-slate-700 mb-1">
                  Budget Priority
                </label>
                <select
                  id="household-budget"
                  value={householdBudget}
                  onChange={(e) => setHouseholdBudget(e.target.value as HouseholdBudget)}
                  className="w-full px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                >
                  <option value="low">Low (Zero/Low Cost)</option>
                  <option value="medium">Medium (Balanced)</option>
                  <option value="high">High (Maximum Guard)</option>
                </select>
              </div>
            </div>

            {/* Optional Schedule Fields */}
            {hasChildren && (
              <div>
                <label htmlFor="school-schedule" className="block text-xs font-semibold text-slate-700 mb-1">
                  School Schedule Window
                </label>
                <input
                  id="school-schedule"
                  type="text"
                  value={schoolSchedule}
                  onChange={(e) => setSchoolSchedule(e.target.value)}
                  placeholder="e.g. 07:30 - 13:30"
                  className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                />
              </div>
            )}

            <div>
              <label htmlFor="work-schedule" className="block text-xs font-semibold text-slate-700 mb-1">
                Work Schedule Window
              </label>
              <input
                id="work-schedule"
                type="text"
                value={workSchedule}
                onChange={(e) => setWorkSchedule(e.target.value)}
                placeholder="e.g. 09:00 - 18:00"
                className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
              />
            </div>

            {/* Language toggle */}
            <div>
              <label htmlFor="preferred-lang" className="block text-xs font-semibold text-slate-700 mb-1">
                Advisory Language
              </label>
              <select
                id="preferred-lang"
                value={preferredLanguage}
                onChange={(e) => setPreferredLanguage(e.target.value)}
                className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
              >
                <option value="en">English</option>
                <option value="hi">हिंदी (Hindi)</option>
              </select>
            </div>

            {/* Generate Button */}
            <button
              type="submit"
              disabled={isSubmitting || !stationId}
              className="w-full mt-4 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg shadow-sm hover:shadow transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Evaluating Official Guidelines...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Generate Protection Plan
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Column: Generated Plan Presentation (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          {planResult ? (
            <>
              {/* Summary Header Card */}
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pb-3 border-b border-slate-100">
                  <div>
                    <span className="text-xs uppercase font-bold text-slate-400">Evaluated Ambient Condition</span>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-lg font-bold text-slate-900">{planResult.station_name}</span>
                      <span
                        className="px-2 py-0.5 rounded text-xs font-bold"
                        style={{ backgroundColor: aqiBand.bgHex, color: aqiBand.textHex }}
                      >
                        AQI {planResult.aqi_context.overall_aqi || '401+'} ({planResult.aqi_context.category})
                      </span>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-xs text-slate-400">Action Priority</span>
                    <div className="text-sm font-extrabold text-blue-700 bg-blue-50 px-2.5 py-0.5 rounded border border-blue-200 mt-0.5">
                      {planResult.action_priority}
                    </div>
                  </div>
                </div>

                {/* Public Health Summary */}
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-700 leading-relaxed">
                  <span className="font-bold text-slate-900">NCDC Health Summary: </span>
                  {planResult.public_health_summary}
                </div>

                {/* General vs Vulnerable Advisories */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded-lg bg-blue-50/50 border border-blue-100 space-y-1">
                    <span className="font-bold text-blue-900">General Population:</span>
                    <p className="text-slate-700 leading-relaxed">{planResult.general_population_advisory}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-amber-50/50 border border-amber-100 space-y-1">
                    <span className="font-bold text-amber-900">Vulnerable Members (Children & Seniors):</span>
                    <p className="text-slate-700 leading-relaxed">{planResult.vulnerable_population_advisory}</p>
                  </div>
                </div>

                {/* Diurnal Timing Guidance */}
                {planResult.conditional_timing_guidance && Object.keys(planResult.conditional_timing_guidance).length > 0 && (
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-2">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800">
                      <Clock className="w-3.5 h-3.5 text-blue-600" />
                      <span>Conditional Diurnal Timing Windows (NCDC 2025)</span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                      {Object.entries(planResult.conditional_timing_guidance).map(([timeSlot, note]) => (
                        <div key={timeSlot} className="p-2 bg-white rounded border border-slate-100">
                          <span className="font-semibold text-slate-800 capitalize">{timeSlot.replace(/_/g, ' ')}: </span>
                          <span className="text-slate-600">{note}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Actionable Recommendations List */}
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
                <div className="flex items-center gap-2">
                  <Compass className="w-5 h-5 text-blue-600" />
                  <h3 className="text-base font-bold text-slate-900">Actionable Protective Schedule</h3>
                </div>

                <div className="space-y-3">
                  {planResult.recommendations.map((rec, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl bg-slate-50 border border-slate-200 hover:border-slate-300 transition space-y-2"
                    >
                      <div className="flex flex-wrap justify-between items-start gap-2">
                        <div>
                          <span className="text-[11px] font-bold uppercase tracking-wider text-blue-700 bg-blue-100/60 px-2 py-0.5 rounded">
                            {rec.target_group}
                          </span>
                          <h4 className="text-sm font-bold text-slate-900 mt-1">{rec.recommendation}</h4>
                        </div>
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                          Action: {rec.action}
                        </span>
                      </div>

                      <p className="text-xs text-slate-600 leading-relaxed">{rec.reason}</p>

                      {rec.alternative_activity && (
                        <div className="text-xs text-emerald-800 bg-emerald-50/60 p-2 rounded border border-emerald-100">
                          <span className="font-semibold">Safer Alternative: </span>
                          {rec.alternative_activity}
                        </div>
                      )}

                      {rec.practical_steps && rec.practical_steps.length > 0 && (
                        <div className="pt-1">
                          <span className="text-[11px] font-bold text-slate-700">Step-by-step mitigation:</span>
                          <ul className="mt-1 space-y-1">
                            {rec.practical_steps.map((step, sIdx) => (
                              <li key={sIdx} className="text-xs text-slate-600 flex items-start gap-1.5">
                                <CheckCircle className="w-3.5 h-3.5 text-blue-500 flex-shrink-0 mt-0.5" />
                                <span>{step}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* General Household Practices */}
              {planResult.general_household_practices && planResult.general_household_practices.length > 0 && (
                <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-3">
                  <h3 className="text-sm font-bold text-slate-900">Standard Non-Pharmacological Practices</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    {planResult.general_household_practices.map((practice, pIdx) => (
                      <div key={pIdx} className="p-2.5 bg-slate-50 rounded-lg border border-slate-100 text-slate-700 flex items-start gap-2">
                        <ChevronRight className="w-3.5 h-3.5 text-blue-500 flex-shrink-0 mt-0.5" />
                        <span>{practice}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Authoritative Traceability & Citation */}
              <div className="bg-slate-50 rounded-xl border border-slate-200 p-4 text-xs text-slate-500 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-bold text-slate-700">
                    Source: {planResult.structured_advisory_reference.issuing_organization} (
                    {planResult.structured_advisory_reference.publication_year})
                  </span>
                  <a
                    href={planResult.structured_advisory_reference.public_source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline inline-flex items-center gap-1 font-medium"
                  >
                    View Official Health Advisory PDF <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <p className="text-[11px] text-slate-400">
                  Document: {planResult.structured_advisory_reference.document_title} • Section:{' '}
                  {planResult.structured_advisory_reference.relevant_section}
                </p>
              </div>
            </>
          ) : (
            /* Empty State */
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center space-y-4">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-50 text-blue-600">
                <CalendarClock className="w-8 h-8" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h3 className="text-lg font-bold text-slate-900">Awaiting Household Profile</h3>
                <p className="text-xs text-slate-500">
                  Select your monitoring station and family composition, then click &ldquo;Generate Protection Plan&rdquo; to compute condition-based schedules based on official CPCB & NCDC guidelines.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

import test from 'node:test';
import assert from 'node:assert';
import {
  API_BASE_URL,
  fetchHealthCheck,
  aqiApi,
  plannerApi,
  advisorApi,
  transportApi,
  impactApi,
  assistantApi,
} from '../src/services/api.ts';

// Helper to mock fetch with recorded calls
function createMockFetch(handler: (url: string, init?: RequestInit) => { status?: number; json?: any; headers?: Record<string, string>; text?: string }) {
  const calls: Array<{ url: string; init?: RequestInit }> = [];

  const mock = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = typeof input === 'string' ? input : input.toString();
    calls.push({ url, init });

    const result = handler(url, init);
    const status = result.status ?? 200;
    const ok = status >= 200 && status < 300;
    const headers = new Headers(result.headers || {});

    return {
      ok,
      status,
      statusText: ok ? 'OK' : 'Error',
      headers,
      json: async () => result.json ?? {},
      text: async () => result.text ?? JSON.stringify(result.json ?? {}),
    } as unknown as Response;
  };

  return { mock, calls };
}

test('fetchHealthCheck: requests GET /health and returns data', async () => {
  const originalFetch = globalThis.fetch;
  const { mock, calls } = createMockFetch((url, init) => {
    assert.strictEqual(url, `${API_BASE_URL}/health`);
    assert.strictEqual(init?.method || 'GET', 'GET');
    return { json: { status: 'healthy', app_name: 'SmogShield AI' } };
  });

  globalThis.fetch = mock;
  try {
    const res = await fetchHealthCheck();
    assert.strictEqual(res.status, 'healthy');
    assert.strictEqual(calls.length, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('aqiApi.listStations: requests GET /aqi/stations with query params', async () => {
  const originalFetch = globalThis.fetch;
  const { mock, calls } = createMockFetch((url) => {
    assert.strictEqual(url, `${API_BASE_URL}/aqi/stations?city=Delhi&provider=cpcb_datagov`);
    return { json: { total: 1, stations: [], provider: 'cpcb_datagov', demo_mode: false, warnings: [] } };
  });

  globalThis.fetch = mock;
  try {
    const res = await aqiApi.listStations({ city: 'Delhi', provider: 'cpcb_datagov' });
    assert.strictEqual(res.total, 1);
    assert.strictEqual(calls.length, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('aqiApi.getStationAqi: requests GET /aqi/station/:station_id encoded', async () => {
  const originalFetch = globalThis.fetch;
  const { mock, calls } = createMockFetch((url) => {
    assert.strictEqual(url, `${API_BASE_URL}/aqi/station/cpcb_delhi_ito`);
    return { json: { category: 'Poor', overall_aqi: 240, is_exact: true } };
  });

  globalThis.fetch = mock;
  try {
    const res = await aqiApi.getStationAqi('cpcb_delhi_ito');
    assert.strictEqual(res.category, 'Poor');
    assert.strictEqual(res.overall_aqi, 240);
    assert.strictEqual(calls.length, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('aqiApi.calculateAqi: requests POST /aqi/calculate with measurements body', async () => {
  const originalFetch = globalThis.fetch;
  const { mock, calls } = createMockFetch((url, init) => {
    assert.strictEqual(url, `${API_BASE_URL}/aqi/calculate`);
    assert.strictEqual(init?.method, 'POST');
    const body = JSON.parse(init?.body as string);
    assert.strictEqual(body.measurements.length, 1);
    assert.strictEqual(body.measurements[0].pollutant, 'PM2.5');
    return { json: { overall_aqi: 150, category: 'Moderate', is_exact: true } };
  });

  globalThis.fetch = mock;
  try {
    const res = await aqiApi.calculateAqi({
      measurements: [{ pollutant: 'PM2.5', value: 65, unit: 'µg/m³' }],
    });
    assert.strictEqual(res.overall_aqi, 150);
    assert.strictEqual(calls.length, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('plannerApi.generate: requests POST /planner/generate with full payload', async () => {
  const originalFetch = globalThis.fetch;
  const { mock, calls } = createMockFetch((url, init) => {
    assert.strictEqual(url, `${API_BASE_URL}/planner/generate`);
    assert.strictEqual(init?.method, 'POST');
    const body = JSON.parse(init?.body as string);
    assert.strictEqual(body.station_id, 'cpcb_delhi_ito');
    assert.strictEqual(body.family_size, 4);
    assert.strictEqual(body.has_children, true);
    return { json: { station_id: 'cpcb_delhi_ito', action_priority: 'HIGH', recommendations: [] } };
  });

  globalThis.fetch = mock;
  try {
    const res = await plannerApi.generate({
      station_id: 'cpcb_delhi_ito',
      family_size: 4,
      has_children: true,
      has_older_adults: false,
      household_budget: 'medium',
      commute_method: 'metro',
    });
    assert.strictEqual(res.action_priority, 'HIGH');
    assert.strictEqual(calls.length, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('advisorApi.assessIndoor: requests POST /advisor/indoor-assessment', async () => {
  const originalFetch = globalThis.fetch;
  const { mock, calls } = createMockFetch((url, init) => {
    assert.strictEqual(url, `${API_BASE_URL}/advisor/indoor-assessment`);
    assert.strictEqual(init?.method, 'POST');
    const body = JSON.parse(init?.body as string);
    assert.strictEqual(body.room_length_m, 5);
    assert.strictEqual(body.room_width_m, 4);
    assert.strictEqual(body.ceiling_height_m, 3);
    assert.strictEqual(body.cadr, 300);
    return { json: { room_volume_m3: 60, calculated_ach: 5.0 } };
  });

  globalThis.fetch = mock;
  try {
    const res = await advisorApi.assessIndoor({
      room_length_m: 5,
      room_width_m: 4,
      ceiling_height_m: 3,
      has_air_purifier: true,
      cadr: 300,
      cadr_unit: 'm3/h',
    });
    assert.strictEqual(res.room_volume_m3, 60);
    assert.strictEqual(res.calculated_ach, 5.0);
    assert.strictEqual(calls.length, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('transportApi.getEmissionFactors: requests GET /transport/emission-factors with query', async () => {
  const originalFetch = globalThis.fetch;
  const { mock, calls } = createMockFetch((url) => {
    assert.strictEqual(url, `${API_BASE_URL}/transport/emission-factors?mode=metro`);
    return { json: { total_factors: 1, factors: [], registry_notes: [] } };
  });

  globalThis.fetch = mock;
  try {
    const res = await transportApi.getEmissionFactors({ mode: 'metro' });
    assert.strictEqual(res.total_factors, 1);
    assert.strictEqual(calls.length, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('transportApi.compare: requests POST /transport/compare', async () => {
  const originalFetch = globalThis.fetch;
  const { mock, calls } = createMockFetch((url, init) => {
    assert.strictEqual(url, `${API_BASE_URL}/transport/compare`);
    assert.strictEqual(init?.method, 'POST');
    const body = JSON.parse(init?.body as string);
    assert.strictEqual(body.station_id, 'cpcb_delhi_ito');
    assert.strictEqual(body.current_mode, 'petrol_car');
    assert.strictEqual(body.distance_km, 12);
    assert.deepStrictEqual(body.alternatives, ['metro']);
    return { json: { station_id: 'cpcb_delhi_ito', avoided_comparisons: [] } };
  });

  globalThis.fetch = mock;
  try {
    const res = await transportApi.compare({
      station_id: 'cpcb_delhi_ito',
      current_mode: 'petrol_car',
      distance_km: 12,
      alternatives: ['metro'],
    });
    assert.strictEqual(res.station_id, 'cpcb_delhi_ito');
    assert.strictEqual(calls.length, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('impactApi.createSession: requests POST /impact/sessions', async () => {
  const originalFetch = globalThis.fetch;
  const { mock, calls } = createMockFetch((url, init) => {
    assert.strictEqual(url, `${API_BASE_URL}/impact/sessions`);
    assert.strictEqual(init?.method, 'POST');
    return { json: { session_id: 'uuid-1234', storage_disclaimer: 'disclaimer' } };
  });

  globalThis.fetch = mock;
  try {
    const res = await impactApi.createSession();
    assert.strictEqual(res.session_id, 'uuid-1234');
    assert.strictEqual(calls.length, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('impactApi.logTrip: sends X-Session-ID, Idempotency-Key headers and body', async () => {
  const originalFetch = globalThis.fetch;
  const { mock, calls } = createMockFetch((url, init) => {
    assert.strictEqual(url, `${API_BASE_URL}/impact/log-trip`);
    assert.strictEqual(init?.method, 'POST');
    const headers = init?.headers as Record<string, string>;
    assert.strictEqual(headers['X-Session-ID'], 'session-abc');
    assert.strictEqual(headers['Idempotency-Key'], 'custom-key-1');
    const body = JSON.parse(init?.body as string);
    assert.strictEqual(body.mode, 'metro');
    assert.strictEqual(body.distance_km, 10);
    return { json: { session_id: 'session-abc', message: 'Logged' } };
  });

  globalThis.fetch = mock;
  try {
    const res = await impactApi.logTrip(
      { mode: 'metro', distance_km: 10 },
      'session-abc',
      'custom-key-1'
    );
    assert.strictEqual(res.session_id, 'session-abc');
    assert.strictEqual(calls.length, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('impactApi.logTrip: generates idempotency key if omitted', async () => {
  const originalFetch = globalThis.fetch;
  let sentKey = '';
  const { mock } = createMockFetch((_url, init) => {
    const headers = init?.headers as Record<string, string>;
    sentKey = headers['Idempotency-Key'];
    return { json: { session_id: 'session-xyz', message: 'Logged' } };
  });

  globalThis.fetch = mock;
  try {
    await impactApi.logTrip({ mode: 'metro', distance_km: 5 }, 'session-xyz');
    assert.ok(sentKey.length > 0, 'Idempotency key should have been generated');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('impactApi.logTrip: throws if sessionId is empty', async () => {
  await assert.rejects(
    async () => {
      await impactApi.logTrip({ mode: 'metro', distance_km: 5 }, '');
    },
    { message: /A valid session ID is required/ }
  );
});

test('impactApi.getSessionSummary: requests GET /impact/session-summary with X-Session-ID', async () => {
  const originalFetch = globalThis.fetch;
  const { mock, calls } = createMockFetch((url, init) => {
    assert.strictEqual(url, `${API_BASE_URL}/impact/session-summary`);
    assert.strictEqual(init?.method, 'GET');
    const headers = init?.headers as Record<string, string>;
    assert.strictEqual(headers['X-Session-ID'], 'session-summary-id');
    return { json: { session_id: 'session-summary-id', completed_action_count: 2, actual_total_emissions_kg_co2: 1.5 } };
  });

  globalThis.fetch = mock;
  try {
    const res = await impactApi.getSessionSummary('session-summary-id');
    assert.strictEqual(res.completed_action_count, 2);
    assert.strictEqual(calls.length, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('impactApi.getSessionSummary: throws if sessionId is empty', async () => {
  await assert.rejects(
    async () => {
      await impactApi.getSessionSummary('');
    },
    { message: /A valid session ID is required/ }
  );
});

test('assistantApi.chat: calls POST /assistant/chat and attaches X-Session-ID only when requested', async () => {
  const originalFetch = globalThis.fetch;
  let headersPassed: Record<string, string> | undefined;

  const { mock } = createMockFetch((url, init) => {
    assert.strictEqual(url, `${API_BASE_URL}/assistant/chat`);
    assert.strictEqual(init?.method, 'POST');
    headersPassed = init?.headers as Record<string, string>;
    return { json: { gemini_explanation: 'Air quality advice', citations: [] } };
  });

  globalThis.fetch = mock;
  try {
    // Turn 1: Without impact summary -> no X-Session-ID header
    await assistantApi.chat({ message: 'What is AQI?' }, 'session-should-not-be-sent');
    assert.strictEqual(headersPassed?.['X-Session-ID'], undefined);

    // Turn 2: With impact summary requested -> X-Session-ID sent
    await assistantApi.chat(
      { message: 'What is my footprint?', context_inputs: { include_impact_summary: true } },
      'session-active'
    );
    assert.strictEqual(headersPassed?.['X-Session-ID'], 'session-active');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('assistantApi.getHealth: calls GET /assistant/health', async () => {
  const originalFetch = globalThis.fetch;
  const { mock, calls } = createMockFetch((url) => {
    assert.strictEqual(url, `${API_BASE_URL}/assistant/health`);
    return { json: { status: 'READY', configured_model: 'gemini-1.5-flash', api_key_configured: false } };
  });

  globalThis.fetch = mock;
  try {
    const res = await assistantApi.getHealth();
    assert.strictEqual(res.status, 'READY');
    assert.strictEqual(calls.length, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('Error handling: formatted Pydantic validation errors (422)', async () => {
  const originalFetch = globalThis.fetch;
  const { mock } = createMockFetch(() => ({
    status: 422,
    json: {
      detail: [
        { loc: ['body', 'room_length_m'], msg: 'Input should be greater than 0', type: 'greater_than' },
      ],
    },
  }));

  globalThis.fetch = mock;
  try {
    await assert.rejects(
      async () => {
        await advisorApi.assessIndoor({
          room_length_m: -1,
          room_width_m: 4,
          ceiling_height_m: 3,
        });
      },
      { message: /Validation failed: room_length_m: Input should be greater than 0/ }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('Error handling: rate limiting (429) with Retry-After header', async () => {
  const originalFetch = globalThis.fetch;
  const { mock } = createMockFetch(() => ({
    status: 429,
    headers: { 'Retry-After': '15' },
    json: { detail: 'Too many requests' },
  }));

  globalThis.fetch = mock;
  try {
    await assert.rejects(
      async () => {
        await assistantApi.chat({ message: 'Hello' });
      },
      { message: /Rate limit exceeded: Too many requests Please wait 15 seconds before trying again\./ }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

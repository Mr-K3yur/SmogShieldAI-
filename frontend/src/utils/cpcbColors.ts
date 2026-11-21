import { NAQICategory } from '../types';

export interface NAQIBand {
  category: NAQICategory;
  min: number;
  max: number;
  bgHex: string;
  textHex: string;
  advisory: string;
}

export const CPCB_NAQI_BANDS: Record<NAQICategory, NAQIBand> = {
  Good: {
    category: 'Good',
    min: 0,
    max: 50,
    bgHex: '#00B050',
    textHex: '#FFFFFF',
    advisory: 'Minimal health impact.'
  },
  Satisfactory: {
    category: 'Satisfactory',
    min: 51,
    max: 100,
    bgHex: '#92D050',
    textHex: '#000000',
    advisory: 'Minor breathing discomfort to sensitive people.'
  },
  Moderate: {
    category: 'Moderate',
    min: 101,
    max: 200,
    bgHex: '#FFFF00',
    textHex: '#000000',
    advisory: 'Breathing discomfort to people with lungs, asthma, and heart diseases.'
  },
  Poor: {
    category: 'Poor',
    min: 201,
    max: 300,
    bgHex: '#FF9900',
    textHex: '#000000',
    advisory: 'Breathing discomfort to most people on prolonged outdoor exposure.'
  },
  'Very Poor': {
    category: 'Very Poor',
    min: 301,
    max: 400,
    bgHex: '#FF0000',
    textHex: '#FFFFFF',
    advisory: 'Respiratory illness on prolonged exposure. Limit outdoor exertion.'
  },
  Severe: {
    category: 'Severe',
    min: 401,
    max: 500,
    bgHex: '#C00000',
    textHex: '#FFFFFF',
    advisory: 'Affects healthy people and seriously impacts those with existing respiratory diseases.'
  },
  Unknown: {
    category: 'Unknown',
    min: -1,
    max: -1,
    bgHex: '#64748B',
    textHex: '#FFFFFF',
    advisory: 'Data unavailable or insufficient pollutant coverage per CPCB criteria.'
  }
};

/**
 * Lookup presentation band (colors, text styling, advisory) by backend-provided CPCB category.
 * The backend is the sole authority for calculating sub-indices and categories.
 */
export function getBandForCategory(category: string | null | undefined): NAQIBand {
  if (!category) return CPCB_NAQI_BANDS.Unknown;
  const match = Object.keys(CPCB_NAQI_BANDS).find(
    (key) => key.toLowerCase() === category.toLowerCase()
  );
  return match ? CPCB_NAQI_BANDS[match as NAQICategory] : CPCB_NAQI_BANDS.Unknown;
}

/**
 * Presentation fallback only. Authoritative category must come from backend CPCB engine.
 */
export function getCategoryForAQI(aqi: number | null): NAQICategory {
  if (aqi === null || aqi < 0) return 'Unknown';
  if (aqi <= 50) return 'Good';
  if (aqi <= 100) return 'Satisfactory';
  if (aqi <= 200) return 'Moderate';
  if (aqi <= 300) return 'Poor';
  if (aqi <= 400) return 'Very Poor';
  return 'Severe';
}

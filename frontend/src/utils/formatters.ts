/** Format numerical concentration with units */
export function formatConcentration(value: number | null, unit: string = 'µg/m³'): string {
  if (value === null || value === undefined) return '--';
  return `${value.toFixed(1)} ${unit}`;
}

/** Format ISO timestamp to readable Indian Standard Time */
export function formatToIST(isoString: string): string {
  try {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
      timeZone: 'Asia/Kolkata'
    });
  } catch {
    return isoString;
  }
}

/** Calculate staleness in minutes from UTC timestamp */
export function calculateStalenessMinutes(isoString: string): number {
  try {
    const timestamp = new Date(isoString).getTime();
    const now = Date.now();
    return Math.max(0, Math.floor((now - timestamp) / (1000 * 60)));
  } catch {
    return 0;
  }
}

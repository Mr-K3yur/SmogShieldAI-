import { useState, useEffect } from 'react';
import { fetchHealthCheck } from '../services/api';
import { BackendHealthResponse } from '../types';

export function useHealth() {
  const [health, setHealth] = useState<BackendHealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    fetchHealthCheck()
      .then((data) => {
        if (mounted) {
          setHealth(data);
          setError(null);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to connect');
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  return { health, loading, error };
}

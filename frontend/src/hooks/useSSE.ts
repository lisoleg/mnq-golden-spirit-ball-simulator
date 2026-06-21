import { useState, useEffect, useCallback, useRef } from 'react';

interface SSEData {
  data: any;
  error: string | null;
  connected: boolean;
}

export function useSSE(url: string | null): SSEData {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (!url) return;

    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => {
      setConnected(true);
      setError(null);
    };

    es.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        setData(parsed);
      } catch {
        setData(event.data);
      }
    };

    es.onerror = () => {
      setConnected(false);
      setError('SSE connection error');
      es.close();
      // Auto-reconnect after 3 seconds
      setTimeout(connect, 3000);
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
    };
  }, [connect]);

  return { data, error, connected };
}

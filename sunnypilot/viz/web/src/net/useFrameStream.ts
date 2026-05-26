import { useEffect, useRef, useState } from 'react';
import type { ConnStatus, Frame } from '../types';

export function useFrameStream(path: string) {
  const [frame, setFrame] = useState<Frame | null>(null);
  const [status, setStatus] = useState<ConnStatus>('connecting');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectMs = useRef(500);

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    const connect = () => {
      if (cancelled) return;
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const url = `${proto}://${window.location.host}${path}`;
      setStatus('connecting');
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => {
        setStatus('open');
        reconnectMs.current = 500;
      };
      ws.onmessage = (ev) => {
        try {
          setFrame(JSON.parse(ev.data) as Frame);
        } catch {
          /* drop malformed */
        }
      };
      ws.onerror = () => setStatus('error');
      ws.onclose = () => {
        setStatus('closed');
        if (cancelled) return;
        timer = window.setTimeout(connect, reconnectMs.current);
        reconnectMs.current = Math.min(reconnectMs.current * 2, 8000);
      };
    };

    connect();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      wsRef.current?.close();
    };
  }, [path]);

  return { frame, status };
}

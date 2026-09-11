'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { getVideoJob, listVideoJobs } from '@/lib/api';
import type { VideoJob } from '@/types/api';

export function useVideoJobPolling(jobId: number | null, intervalMs = 2000) {
  const [job, setJob] = useState<VideoJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const stop = useCallback(() => {
    if (timer.current) {
      clearInterval(timer.current);
      timer.current = null;
    }
    setIsPolling(false);
  }, []);

  useEffect(() => {
    if (jobId == null) {
      stop();
      setJob(null);
      return;
    }

    let cancelled = false;
    setIsPolling(true);

    const poll = async () => {
      try {
        const data = await getVideoJob(jobId);
        if (cancelled) return;
        setJob(data);
        setError(null);
        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
          stop();
        }
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : 'Polling error');
      }
    };

    poll();
    timer.current = setInterval(poll, intervalMs);

    return () => {
      cancelled = true;
      stop();
    };
  }, [jobId, intervalMs, stop]);

  return { job, error, isPolling };
}

export function useVideoJobsList(refreshMs = 5000) {
  const [jobs, setJobs] = useState<VideoJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await listVideoJobs(50);
      setJobs(data.jobs);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error loading jobs');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const hasActive = jobs.some((j) => j.status === 'PENDING' || j.status === 'PROCESSING');
    const interval = setInterval(refresh, hasActive ? refreshMs : refreshMs * 6);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh, jobs.length]);

  return { jobs, loading, error, refresh };
}

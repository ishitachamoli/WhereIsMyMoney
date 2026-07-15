'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '@/lib/api';
import { ClassificationJob } from '@/types';

const POLL_INTERVAL_MS = 2000;
const SUCCESS_DISMISS_MS = 5000;

interface ClassificationProgressBannerProps {
  jobId?: string | null;
  onComplete?: () => void;
}

export function ClassificationProgressBanner({ jobId, onComplete }: ClassificationProgressBannerProps) {
  const [job, setJob] = useState<ClassificationJob | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const dismissRef = useRef<NodeJS.Timeout | null>(null);
  const activeJobId = useRef<string | null>(null);

  const fetchJob = useCallback(async (id: string) => {
    try {
      const data = await api.getClassificationJob(id);
      setJob(data);

      if (data.status === 'completed' || data.status === 'failed') {
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
        if (data.status === 'completed') {
          setShowSuccess(true);
          onComplete?.();
          dismissRef.current = setTimeout(() => {
            setDismissed(true);
          }, SUCCESS_DISMISS_MS);
        }
      }
    } catch {
      // Silently ignore polling errors
    }
  }, [onComplete]);

  const checkActiveJob = useCallback(async () => {
    try {
      const data = await api.getActiveClassificationJob();
      if (data && data.id) {
        activeJobId.current = data.id;
        setJob(data);
        setDismissed(false);
        setShowSuccess(false);
        return data.id;
      }
    } catch {
      // No active job
    }
    return null;
  }, []);

  useEffect(() => {
    let targetId = jobId || null;

    const start = async () => {
      if (!targetId) {
        targetId = await checkActiveJob();
      }

      if (!targetId) return;

      activeJobId.current = targetId;
      await fetchJob(targetId);

      pollRef.current = setInterval(() => {
        if (activeJobId.current) {
          fetchJob(activeJobId.current);
        }
      }, POLL_INTERVAL_MS);
    };

    start();

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (dismissRef.current) clearTimeout(dismissRef.current);
    };
  }, [jobId, fetchJob, checkActiveJob]);

  if (dismissed || !job) return null;

  if (job.status === 'failed') {
    return (
      <div className="w-full bg-red-900/40 border-b border-red-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">❌</span>
          <span className="text-sm text-red-200">
            Classification failed: {job.error || 'Unknown error'}
          </span>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-red-300 hover:text-red-100 text-xs font-medium"
        >
          Dismiss
        </button>
      </div>
    );
  }

  if (showSuccess && job.status === 'completed') {
    return (
      <div className="w-full bg-green-900/40 border-b border-green-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">✅</span>
          <span className="text-sm text-green-200">
            Classification complete! {job.total_transactions} transactions categorized by AI.
          </span>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-green-300 hover:text-green-100 text-xs font-medium"
        >
          Dismiss
        </button>
      </div>
    );
  }

  const progressPercent = job.progress_percent || 0;

  return (
    <div className="w-full bg-blue-900/40 border-b border-blue-800 px-4 py-3">
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <span className="text-lg animate-pulse">🤖</span>
          <span className="text-sm text-blue-200">
            AI is classifying your transactions...{' '}
            <span className="font-medium text-blue-100">
              {job.classified_transactions}/{job.total_transactions}
            </span>{' '}
            <span className="text-blue-300">({progressPercent.toFixed(0)}%)</span>
          </span>
        </div>
      </div>
      <div className="h-1.5 bg-blue-950 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${Math.max(progressPercent, 2)}%` }}
        />
      </div>
    </div>
  );
}

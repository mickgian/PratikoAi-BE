'use client';

import { useState, useCallback, useEffect } from 'react';
import {
  getVersion,
  getUnseenReleaseNote,
  markReleaseNoteSeen,
} from '@/lib/api/release-notes';
import type { ReleaseNote, VersionInfo } from '@/lib/api/release-notes';

export function useVersionInfo() {
  const [version, setVersion] = useState<VersionInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    getVersion()
      .then(data => {
        if (mounted) setVersion(data);
      })
      .catch(() => {
        if (mounted) setVersion(null);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  return { version, loading };
}

export function useUnseenReleaseNote(isAuthenticated: boolean) {
  const [unseenNote, setUnseenNote] = useState<ReleaseNote | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      setUnseenNote(null);
      return;
    }

    let mounted = true;
    setLoading(true);
    getUnseenReleaseNote()
      .then(data => {
        if (mounted) setUnseenNote(data);
      })
      .catch(() => {
        if (mounted) setUnseenNote(null);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [isAuthenticated]);

  const dismiss = useCallback(async (version: string) => {
    try {
      await markReleaseNoteSeen(version);
      setUnseenNote(null);
    } catch {
      setUnseenNote(null);
    }
  }, []);

  return { unseenNote, loading, dismiss };
}

'use client';

import { useState, useEffect } from 'react';
import { getVersion } from '@/lib/api/release-notes';
import type { VersionInfo } from '@/lib/api/release-notes';

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

// src/hooks/useExpertStatus.ts
'use client';

import { useState, useEffect } from 'react';
import { isUserSuperUser } from '@/lib/api/expertFeedback';

/**
 * Hook to check if the current user is a SUPER_USER
 * Returns loading state and super user status
 *
 * SUPER_USER users can provide expert feedback on AI responses.
 * This replaces the old trust_score check with role-based authorization.
 */
export function useExpertStatus() {
  const [isSuperUser, setIsSuperUser] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Keep old isExpert for backward compatibility
  const isExpert = isSuperUser;

  useEffect(() => {
    let mounted = true;

    async function checkSuperUserStatus() {
      console.log('🔄 [useExpertStatus] Starting super user check...');
      try {
        setIsLoading(true);
        const superUserStatus = await isUserSuperUser();

        console.log(
          `✅ [useExpertStatus] Check complete: isSuperUser=${superUserStatus}`
        );

        if (mounted) {
          setIsSuperUser(superUserStatus);
          setError(null);
        }
      } catch (err) {
        console.error(
          '❌ [useExpertStatus] Failed to check super user status:',
          err
        );
        if (mounted) {
          setIsSuperUser(false);
          setError(
            err instanceof Error ? err.message : 'Failed to check user role'
          );
        }
      } finally {
        if (mounted) {
          console.log('🏁 [useExpertStatus] Setting isLoading=false');
          setIsLoading(false);
        }
      }
    }

    checkSuperUserStatus();

    return () => {
      mounted = false;
    };
  }, []);

  return {
    isSuperUser,
    isExpert, // Backward compatibility alias
    isLoading,
    error,
  };
}

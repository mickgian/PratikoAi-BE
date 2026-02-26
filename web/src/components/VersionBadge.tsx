'use client';

import React from 'react';

interface VersionBadgeProps {
  version: string;
}

export function VersionBadge({ version }: VersionBadgeProps) {
  if (!version) return null;

  return <span className="text-sm text-gray-500">v{version}</span>;
}

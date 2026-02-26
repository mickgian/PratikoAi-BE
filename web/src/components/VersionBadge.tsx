'use client';

import React from 'react';
import Link from 'next/link';
import { Sparkles } from 'lucide-react';

interface VersionBadgeProps {
  version: string;
}

export function VersionBadge({ version }: VersionBadgeProps) {
  if (!version) return null;

  return (
    <div className="flex items-center space-x-3 text-sm">
      <span className="text-gray-500">v{version}</span>
      <Link
        href="/novita"
        className="text-[#D4A574] hover:text-[#2A5D67] transition-colors duration-200 flex items-center space-x-1"
        aria-label="Novità"
      >
        <Sparkles className="w-3.5 h-3.5" />
        <span>Novità</span>
      </Link>
    </div>
  );
}

'use client'

import React from 'react'

interface PratikoLogoProps {
  className?: string
  animated?: boolean
}

/**
 * PratikoAI Logo Component
 * 
 * Features:
 * - Scalable SVG logo
 * - Optional animation for typing indicator
 * - Blu Petrolio color scheme
 * - Professional appearance
 */
export function PratikoLogo({ className = '', animated = false }: PratikoLogoProps) {
  return (
    <div 
      className={`inline-flex items-center justify-center ${className} ${animated ? 'animate-pulse' : ''}`}
      data-testid="pratiko-logo"
    >
      {/* Simplified P logo in a circle */}
      <div 
        className={`
          w-6 h-6 
          bg-[#2A5D67] 
          text-white 
          rounded-full 
          flex 
          items-center 
          justify-center 
          text-sm 
          font-bold
          shadow-sm
          ${animated ? 'animate-pulse' : ''}
        `}
      >
        P
      </div>
    </div>
  )
}
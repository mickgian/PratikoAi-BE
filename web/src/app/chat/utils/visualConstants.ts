/**
 * Visual Constants for PratikoAI Chat
 * Centralizes all design tokens for consistency
 */

// CHAT_REQUIREMENTS.md Color Palette
export const COLORS = {
  // Primary Colors
  BLU_PETROLIO: '#2A5D67',
  AVORIO: '#F8F5F1',
  DARK_SLATE: '#1E293B',
  GRIGIO_TORTORA: '#C4BDB4',
  
  // Extended Palette
  BLU_PETROLIO_LIGHT: '#3A7A89',
  BLU_PETROLIO_DARK: '#1A4D57',
  ORO_ANTICO: '#d4a574',
  
  // Semantic Colors
  SUCCESS: '#10B981',
  WARNING: '#F59E0B',
  ERROR: '#EF4444',
  INFO: '#3B82F6',
  
  // Text Colors
  TEXT_PRIMARY: '#1E293B',
  TEXT_SECONDARY: '#64748B',
  TEXT_MUTED: '#94A3B8',
  TEXT_DISABLED: '#CBD5E1',
  
  // Background Colors
  BG_PRIMARY: '#FFFFFF',
  BG_SECONDARY: '#F8F5F1',
  BG_MUTED: '#F1F5F9',
  BG_HOVER: '#F8FAFC'
} as const

// Typography Scale
export const TYPOGRAPHY = {
  FONT_FAMILY: {
    SANS: '"Inter", "system-ui", sans-serif',
    MONO: '"Fira Code", "Monaco", monospace'
  },
  
  FONT_SIZE: {
    XS: '0.75rem',    // 12px
    SM: '0.875rem',   // 14px
    BASE: '1rem',     // 16px
    LG: '1.125rem',   // 18px
    XL: '1.25rem',    // 20px
    '2XL': '1.5rem',  // 24px
    '3XL': '1.875rem' // 30px
  },
  
  LINE_HEIGHT: {
    TIGHT: '1.25',
    NORMAL: '1.5',
    RELAXED: '1.625',
    LOOSE: '2'
  },
  
  FONT_WEIGHT: {
    NORMAL: '400',
    MEDIUM: '500',
    SEMIBOLD: '600',
    BOLD: '700'
  }
} as const

// Spacing Scale (based on Tailwind's 4px scale)
export const SPACING = {
  XS: '0.25rem',    // 4px
  SM: '0.5rem',     // 8px
  MD: '0.75rem',    // 12px
  LG: '1rem',       // 16px
  XL: '1.5rem',     // 24px
  '2XL': '2rem',    // 32px
  '3XL': '3rem',    // 48px
  '4XL': '4rem'     // 64px
} as const

// Message Dimensions
export const MESSAGE = {
  MAX_WIDTH: {
    MOBILE: '280px',
    DESKTOP: '600px'
  },
  
  CONTAINER_MAX_WIDTH: '1024px',
  
  BORDER: {
    RADIUS: '1rem',     // 16px
    RADIUS_SM: '0.375rem', // 6px
    WIDTH: '3px'
  }
} as const

// Animation Durations
export const ANIMATION = {
  DURATION: {
    FAST: '150ms',
    NORMAL: '300ms',
    SLOW: '500ms'
  },
  
  EASING: {
    EASE_IN_OUT: 'cubic-bezier(0.4, 0, 0.2, 1)',
    EASE_OUT: 'cubic-bezier(0, 0, 0.2, 1)',
    EASE_IN: 'cubic-bezier(0.4, 0, 1, 1)',
    BOUNCE: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)'
  },
  
  // Typing Animation
  TYPING: {
    SPEED: 75, // characters per second (ChatGPT-level performance)
    CURSOR_BLINK: '1s'
  }
} as const

// Breakpoints (matching Tailwind)
export const BREAKPOINTS = {
  SM: '640px',
  MD: '768px',
  LG: '1024px',
  XL: '1280px',
  '2XL': '1536px'
} as const

// Shadow Definitions
export const SHADOWS = {
  SM: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  MD: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  LG: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  XL: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)'
} as const

// Z-Index Scale
export const Z_INDEX = {
  DROPDOWN: 1000,
  STICKY: 1020,
  FIXED: 1030,
  MODAL_BACKDROP: 1040,
  MODAL: 1050,
  POPOVER: 1060,
  TOOLTIP: 1070,
  TOAST: 1080
} as const

// Professional polish utilities
export const POLISH = {
  // Smooth transitions for professional feel
  TRANSITIONS: {
    ALL: `all ${ANIMATION.DURATION.NORMAL} ${ANIMATION.EASING.EASE_IN_OUT}`,
    COLORS: `color ${ANIMATION.DURATION.FAST} ${ANIMATION.EASING.EASE_IN_OUT}, background-color ${ANIMATION.DURATION.FAST} ${ANIMATION.EASING.EASE_IN_OUT}`,
    TRANSFORM: `transform ${ANIMATION.DURATION.NORMAL} ${ANIMATION.EASING.EASE_OUT}`,
    OPACITY: `opacity ${ANIMATION.DURATION.FAST} ${ANIMATION.EASING.EASE_IN_OUT}`
  },
  
  // Hover states
  HOVER: {
    SCALE: 'scale(1.02)',
    SHADOW: SHADOWS.MD,
    OPACITY: '0.8'
  },
  
  // Focus states for accessibility
  FOCUS: {
    RING: `0 0 0 3px ${COLORS.BLU_PETROLIO}33`, // 20% opacity
    OUTLINE: 'none'
  }
} as const

// Italian-specific formatting
export const LOCALIZATION = {
  CURRENCY: {
    SYMBOL: '€',
    POSITION: 'before', // € 1.234,56
    DECIMAL_SEPARATOR: ',',
    THOUSAND_SEPARATOR: '.'
  },
  
  TIME: {
    FORMAT: 'HH:mm', // 24-hour format
    LOCALE: 'it-IT'
  },
  
  DATE: {
    FORMAT: 'dd/MM/yyyy',
    LOCALE: 'it-IT'
  }
} as const

// Performance constants
export const PERFORMANCE = {
  // Virtual scrolling thresholds
  VIRTUAL_SCROLL_THRESHOLD: 100,
  
  // Message history limits
  MAX_MESSAGES_IN_MEMORY: 1000,
  MAX_MESSAGES_VISIBLE: 50,
  
  // Debounce timings
  DEBOUNCE: {
    SEARCH: 300,
    SCROLL: 100,
    RESIZE: 150
  },
  
  // Lazy loading
  INTERSECTION_THRESHOLD: 0.1,
  INTERSECTION_ROOT_MARGIN: '50px'
} as const

// Export commonly used combinations
export const THEME = {
  USER_MESSAGE: {
    background: COLORS.ORO_ANTICO,
    color: COLORS.TEXT_PRIMARY,
    alignment: 'right'
  },
  
  AI_MESSAGE: {
    background: COLORS.BG_PRIMARY,
    color: COLORS.TEXT_PRIMARY,
    borderColor: COLORS.BLU_PETROLIO,
    alignment: 'left'
  },
  
  TYPING_CURSOR: {
    color: COLORS.BLU_PETROLIO,
    animation: `blink ${ANIMATION.TYPING.CURSOR_BLINK} infinite`
  }
} as const
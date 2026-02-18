/**
 * Design Tokens - PratikoAI Design System
 * Extracted from Figma design and applied consistently across the app
 */

export const tokens = {
  // Colors
  colors: {
    primary: {
      blue: '#0066FF',
      blueHover: '#0052CC',
    },
    secondary: {
      successGreen: '#00D084',
      successGreenHover: '#00B574',
      accentYellow: '#FFB800',
    },
    text: {
      primary: '#0A0A0A',
      secondary: '#6B7280',
    },
    background: {
      white: '#FFFFFF',
      alt: '#F9FAFB',
    },
    border: {
      light: '#E5E7EB',
    },
    system: {
      destructive: '#d4183d',
      destructiveForeground: '#ffffff',
      switchBackground: '#cbced4',
    },
    darkMode: {
      secondary: '#1F2937',
      border: '#374151',
    },
    chart: {
      1: 'oklch(0.646 0.222 41.116)',
      2: 'oklch(0.6 0.118 184.704)',
      3: 'oklch(0.398 0.07 227.392)',
      4: 'oklch(0.828 0.189 84.429)',
      5: 'oklch(0.769 0.188 70.08)',
    },
    gradients: {
      primary: 'linear-gradient(135deg, #0066FF 0%, #0052CC 100%)',
      success: 'linear-gradient(135deg, #00D084 0%, #00B574 100%)',
    },
  },

  // Typography
  typography: {
    fontFamily: {
      primary: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif',
    },
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      '2xl': '1.5rem',
      '3xl': '1.875rem',
      '4xl': '2.25rem',
      '5xl': '3rem',
      '6xl': '3.75rem',
      '7xl': '4.5rem',
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
      black: 900,
    },
    lineHeight: {
      tight: 1.1,
      snug: 1.2,
      normal: 1.3,
      relaxed: 1.4,
      loose: 1.5,
      extraLoose: 1.6,
    },
    letterSpacing: {
      tight: '-0.02em',
      normal: '0',
      wide: '0.025em',
    },
  },

  // Spacing
  spacing: {
    xs: '0.25rem',    // 4px
    sm: '0.5rem',     // 8px
    md: '1rem',       // 16px
    lg: '1.5rem',     // 24px
    xl: '2rem',       // 32px
    '2xl': '3rem',    // 48px
    '3xl': '4rem',    // 64px
    '4xl': '5rem',    // 80px
    '5xl': '6rem',    // 96px
    '6xl': '8rem',    // 128px
  },

  // Border Radius
  borderRadius: {
    sm: 'calc(8px - 4px)',
    md: 'calc(8px - 2px)',
    lg: '8px',
    xl: 'calc(8px + 4px)',
    full: '9999px',
  },

  // Shadows
  boxShadow: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
    '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
  },

  // Animation Durations
  animation: {
    duration: {
      fast: '150ms',
      normal: '300ms',
      slow: '500ms',
    },
    easing: {
      easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
      easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
      easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    },
  },

  // Breakpoints
  breakpoints: {
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    '2xl': '1536px',
  },
} as const;

// CSS Custom Property helpers
export const cssVars = {
  // Generate CSS custom properties for colors
  color: (colorPath: string) => `var(--color-${colorPath})`,
  
  // Generate CSS custom properties for spacing
  spacing: (size: keyof typeof tokens.spacing) => `var(--spacing-${size})`,
  
  // Generate CSS custom properties for typography
  fontSize: (size: keyof typeof tokens.typography.fontSize) => `var(--font-size-${size})`,
  
  // Generate CSS custom properties for border radius
  borderRadius: (size: keyof typeof tokens.borderRadius) => `var(--radius-${size})`,
} as const;

// Utility functions for common patterns
export const tokenUtils = {
  // Get gradient background class
  gradient: (type: 'primary' | 'success') => {
    return type === 'primary' ? 'bg-gradient-primary' : 'bg-gradient-success';
  },
  
  // Get text color classes
  textColor: (variant: 'primary' | 'secondary' | 'blue' | 'success') => {
    switch (variant) {
      case 'primary': return 'text-gray-900';
      case 'secondary': return 'text-gray-600';
      case 'blue': return 'text-blue-600';
      case 'success': return 'text-green-600';
      default: return 'text-gray-900';
    }
  },
  
  // Get button size classes
  buttonSize: (size: 'sm' | 'md' | 'lg') => {
    switch (size) {
      case 'sm': return 'h-8 px-3 text-sm';
      case 'md': return 'h-10 px-4 text-base';
      case 'lg': return 'h-14 px-8 text-lg';
      default: return 'h-10 px-4 text-base';
    }
  },
  
  // Get spacing classes
  spacing: (variant: 'section' | 'component' | 'element') => {
    switch (variant) {
      case 'section': return 'py-20 lg:py-32';
      case 'component': return 'py-8 lg:py-12';
      case 'element': return 'py-4';
      default: return 'py-4';
    }
  },
} as const;

export type TokensType = typeof tokens;
export type ColorTokens = typeof tokens.colors;
export type TypographyTokens = typeof tokens.typography;
export type SpacingTokens = typeof tokens.spacing;
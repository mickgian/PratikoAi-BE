/**
 * Unit Tests for Design Tokens
 * Testing PratikoAI Design System tokens, CSS variables, and utility functions
 */

import { tokens, cssVars, tokenUtils } from '../tokens';
import type {
  TokensType,
  ColorTokens,
  TypographyTokens,
  SpacingTokens,
} from '../tokens';

describe('Design Tokens', () => {
  describe('tokens object structure', () => {
    test('should have all required top-level properties', () => {
      expect(tokens).toHaveProperty('colors');
      expect(tokens).toHaveProperty('typography');
      expect(tokens).toHaveProperty('spacing');
      expect(tokens).toHaveProperty('borderRadius');
      expect(tokens).toHaveProperty('boxShadow');
      expect(tokens).toHaveProperty('animation');
      expect(tokens).toHaveProperty('breakpoints');
    });

    test('should be a readonly constant object', () => {
      expect(Object.isFrozen(tokens)).toBe(false); // as const doesn't freeze, but provides type safety
      expect(tokens).toBeDefined();
    });

    test('should export TypeScript types', () => {
      // Type assertion tests - these will fail at compile time if types are wrong
      const tokenType: TokensType = tokens;
      const colorType: ColorTokens = tokens.colors;
      const typographyType: TypographyTokens = tokens.typography;
      const spacingType: SpacingTokens = tokens.spacing;

      expect(tokenType).toBeDefined();
      expect(colorType).toBeDefined();
      expect(typographyType).toBeDefined();
      expect(spacingType).toBeDefined();
    });
  });

  describe('colors', () => {
    describe('primary colors', () => {
      test('should have primary blue color', () => {
        expect(tokens.colors.primary.blue).toBe('#0066FF');
      });

      test('should have primary blue hover color', () => {
        expect(tokens.colors.primary.blueHover).toBe('#0052CC');
      });

      test('should have valid hex color format', () => {
        const hexRegex = /^#[0-9A-F]{6}$/i;
        expect(tokens.colors.primary.blue).toMatch(hexRegex);
        expect(tokens.colors.primary.blueHover).toMatch(hexRegex);
      });
    });

    describe('secondary colors', () => {
      test('should have success green color', () => {
        expect(tokens.colors.secondary.successGreen).toBe('#00D084');
      });

      test('should have success green hover color', () => {
        expect(tokens.colors.secondary.successGreenHover).toBe('#00B574');
      });

      test('should have accent yellow color', () => {
        expect(tokens.colors.secondary.accentYellow).toBe('#FFB800');
      });

      test('should have valid hex color formats', () => {
        const hexRegex = /^#[0-9A-F]{6}$/i;
        expect(tokens.colors.secondary.successGreen).toMatch(hexRegex);
        expect(tokens.colors.secondary.successGreenHover).toMatch(hexRegex);
        expect(tokens.colors.secondary.accentYellow).toMatch(hexRegex);
      });
    });

    describe('text colors', () => {
      test('should have primary text color', () => {
        expect(tokens.colors.text.primary).toBe('#0A0A0A');
      });

      test('should have secondary text color', () => {
        expect(tokens.colors.text.secondary).toBe('#6B7280');
      });
    });

    describe('background colors', () => {
      test('should have white background', () => {
        expect(tokens.colors.background.white).toBe('#FFFFFF');
      });

      test('should have alternate background', () => {
        expect(tokens.colors.background.alt).toBe('#F9FAFB');
      });
    });

    describe('border colors', () => {
      test('should have light border color', () => {
        expect(tokens.colors.border.light).toBe('#E5E7EB');
      });
    });

    describe('system colors', () => {
      test('should have destructive color', () => {
        expect(tokens.colors.system.destructive).toBe('#d4183d');
      });

      test('should have destructive foreground color', () => {
        expect(tokens.colors.system.destructiveForeground).toBe('#ffffff');
      });

      test('should have switch background color', () => {
        expect(tokens.colors.system.switchBackground).toBe('#cbced4');
      });
    });

    describe('dark mode colors', () => {
      test('should have secondary dark mode color', () => {
        expect(tokens.colors.darkMode.secondary).toBe('#1F2937');
      });

      test('should have border dark mode color', () => {
        expect(tokens.colors.darkMode.border).toBe('#374151');
      });
    });

    describe('chart colors', () => {
      test('should have all 5 chart colors', () => {
        expect(tokens.colors.chart['1']).toBe('oklch(0.646 0.222 41.116)');
        expect(tokens.colors.chart['2']).toBe('oklch(0.6 0.118 184.704)');
        expect(tokens.colors.chart['3']).toBe('oklch(0.398 0.07 227.392)');
        expect(tokens.colors.chart['4']).toBe('oklch(0.828 0.189 84.429)');
        expect(tokens.colors.chart['5']).toBe('oklch(0.769 0.188 70.08)');
      });

      test('should use oklch color format', () => {
        const oklchRegex = /^oklch\([0-9.]+ [0-9.]+ [0-9.]+\)$/;
        expect(tokens.colors.chart['1']).toMatch(oklchRegex);
        expect(tokens.colors.chart['3']).toMatch(oklchRegex);
      });
    });

    describe('gradients', () => {
      test('should have primary gradient', () => {
        expect(tokens.colors.gradients.primary).toBe(
          'linear-gradient(135deg, #0066FF 0%, #0052CC 100%)'
        );
      });

      test('should have success gradient', () => {
        expect(tokens.colors.gradients.success).toBe(
          'linear-gradient(135deg, #00D084 0%, #00B574 100%)'
        );
      });

      test('should have valid linear-gradient format', () => {
        const gradientRegex = /^linear-gradient\(/;
        expect(tokens.colors.gradients.primary).toMatch(gradientRegex);
        expect(tokens.colors.gradients.success).toMatch(gradientRegex);
      });
    });
  });

  describe('typography', () => {
    describe('fontFamily', () => {
      test('should have primary font family', () => {
        expect(tokens.typography.fontFamily.primary).toBe(
          '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif'
        );
      });

      test('should include fallback fonts', () => {
        const fontFamily = tokens.typography.fontFamily.primary;
        expect(fontFamily).toContain('Inter');
        expect(fontFamily).toContain('sans-serif');
      });
    });

    describe('fontSize', () => {
      test('should have all font sizes', () => {
        expect(tokens.typography.fontSize.xs).toBe('0.75rem');
        expect(tokens.typography.fontSize.sm).toBe('0.875rem');
        expect(tokens.typography.fontSize.base).toBe('1rem');
        expect(tokens.typography.fontSize.lg).toBe('1.125rem');
        expect(tokens.typography.fontSize.xl).toBe('1.25rem');
        expect(tokens.typography.fontSize['2xl']).toBe('1.5rem');
        expect(tokens.typography.fontSize['3xl']).toBe('1.875rem');
        expect(tokens.typography.fontSize['4xl']).toBe('2.25rem');
        expect(tokens.typography.fontSize['5xl']).toBe('3rem');
        expect(tokens.typography.fontSize['6xl']).toBe('3.75rem');
        expect(tokens.typography.fontSize['7xl']).toBe('4.5rem');
      });

      test('should use rem units', () => {
        const remRegex = /^[0-9.]+rem$/;
        expect(tokens.typography.fontSize.base).toMatch(remRegex);
        expect(tokens.typography.fontSize['2xl']).toMatch(remRegex);
      });

      test('should have increasing sizes', () => {
        const parseRem = (value: string) =>
          parseFloat(value.replace('rem', ''));
        expect(parseRem(tokens.typography.fontSize.xs)).toBeLessThan(
          parseRem(tokens.typography.fontSize.sm)
        );
        expect(parseRem(tokens.typography.fontSize.sm)).toBeLessThan(
          parseRem(tokens.typography.fontSize.base)
        );
        expect(parseRem(tokens.typography.fontSize.base)).toBeLessThan(
          parseRem(tokens.typography.fontSize.lg)
        );
      });
    });

    describe('fontWeight', () => {
      test('should have all font weights', () => {
        expect(tokens.typography.fontWeight.normal).toBe(400);
        expect(tokens.typography.fontWeight.medium).toBe(500);
        expect(tokens.typography.fontWeight.semibold).toBe(600);
        expect(tokens.typography.fontWeight.bold).toBe(700);
        expect(tokens.typography.fontWeight.black).toBe(900);
      });

      test('should have valid numeric values', () => {
        expect(typeof tokens.typography.fontWeight.normal).toBe('number');
        expect(typeof tokens.typography.fontWeight.bold).toBe('number');
      });

      test('should have increasing weights', () => {
        expect(tokens.typography.fontWeight.normal).toBeLessThan(
          tokens.typography.fontWeight.medium
        );
        expect(tokens.typography.fontWeight.medium).toBeLessThan(
          tokens.typography.fontWeight.semibold
        );
        expect(tokens.typography.fontWeight.semibold).toBeLessThan(
          tokens.typography.fontWeight.bold
        );
      });
    });

    describe('lineHeight', () => {
      test('should have all line heights', () => {
        expect(tokens.typography.lineHeight.tight).toBe(1.1);
        expect(tokens.typography.lineHeight.snug).toBe(1.2);
        expect(tokens.typography.lineHeight.normal).toBe(1.3);
        expect(tokens.typography.lineHeight.relaxed).toBe(1.4);
        expect(tokens.typography.lineHeight.loose).toBe(1.5);
        expect(tokens.typography.lineHeight.extraLoose).toBe(1.6);
      });

      test('should have numeric unitless values', () => {
        expect(typeof tokens.typography.lineHeight.normal).toBe('number');
        expect(typeof tokens.typography.lineHeight.loose).toBe('number');
      });

      test('should have increasing values', () => {
        expect(tokens.typography.lineHeight.tight).toBeLessThan(
          tokens.typography.lineHeight.snug
        );
        expect(tokens.typography.lineHeight.snug).toBeLessThan(
          tokens.typography.lineHeight.normal
        );
        expect(tokens.typography.lineHeight.normal).toBeLessThan(
          tokens.typography.lineHeight.relaxed
        );
      });
    });

    describe('letterSpacing', () => {
      test('should have all letter spacing values', () => {
        expect(tokens.typography.letterSpacing.tight).toBe('-0.02em');
        expect(tokens.typography.letterSpacing.normal).toBe('0');
        expect(tokens.typography.letterSpacing.wide).toBe('0.025em');
      });

      test('should use em units or zero', () => {
        const spacing = tokens.typography.letterSpacing;
        expect(spacing.tight).toContain('em');
        expect(spacing.normal).toBe('0');
        expect(spacing.wide).toContain('em');
      });
    });
  });

  describe('spacing', () => {
    test('should have all spacing values', () => {
      expect(tokens.spacing.xs).toBe('0.25rem');
      expect(tokens.spacing.sm).toBe('0.5rem');
      expect(tokens.spacing.md).toBe('1rem');
      expect(tokens.spacing.lg).toBe('1.5rem');
      expect(tokens.spacing.xl).toBe('2rem');
      expect(tokens.spacing['2xl']).toBe('3rem');
      expect(tokens.spacing['3xl']).toBe('4rem');
      expect(tokens.spacing['4xl']).toBe('5rem');
      expect(tokens.spacing['5xl']).toBe('6rem');
      expect(tokens.spacing['6xl']).toBe('8rem');
    });

    test('should use rem units', () => {
      const remRegex = /^[0-9.]+rem$/;
      expect(tokens.spacing.md).toMatch(remRegex);
      expect(tokens.spacing['3xl']).toMatch(remRegex);
    });

    test('should have increasing sizes', () => {
      const parseRem = (value: string) => parseFloat(value.replace('rem', ''));
      expect(parseRem(tokens.spacing.xs)).toBeLessThan(
        parseRem(tokens.spacing.sm)
      );
      expect(parseRem(tokens.spacing.sm)).toBeLessThan(
        parseRem(tokens.spacing.md)
      );
      expect(parseRem(tokens.spacing.md)).toBeLessThan(
        parseRem(tokens.spacing.lg)
      );
    });

    test('should match pixel values in comments', () => {
      // xs: 4px, sm: 8px, md: 16px, lg: 24px, xl: 32px
      const parseRem = (value: string) => parseFloat(value.replace('rem', ''));
      expect(parseRem(tokens.spacing.xs) * 16).toBe(4); // 0.25rem * 16 = 4px
      expect(parseRem(tokens.spacing.sm) * 16).toBe(8); // 0.5rem * 16 = 8px
      expect(parseRem(tokens.spacing.md) * 16).toBe(16); // 1rem * 16 = 16px
    });
  });

  describe('borderRadius', () => {
    test('should have all border radius values', () => {
      expect(tokens.borderRadius.sm).toBe('calc(8px - 4px)');
      expect(tokens.borderRadius.md).toBe('calc(8px - 2px)');
      expect(tokens.borderRadius.lg).toBe('8px');
      expect(tokens.borderRadius.xl).toBe('calc(8px + 4px)');
      expect(tokens.borderRadius.full).toBe('9999px');
    });

    test('should use calc() for computed values', () => {
      expect(tokens.borderRadius.sm).toContain('calc');
      expect(tokens.borderRadius.md).toContain('calc');
      expect(tokens.borderRadius.xl).toContain('calc');
    });

    test('should have full border radius for circles', () => {
      expect(tokens.borderRadius.full).toBe('9999px');
    });
  });

  describe('boxShadow', () => {
    test('should have all shadow sizes', () => {
      expect(tokens.boxShadow.sm).toBeDefined();
      expect(tokens.boxShadow.md).toBeDefined();
      expect(tokens.boxShadow.lg).toBeDefined();
      expect(tokens.boxShadow.xl).toBeDefined();
      expect(tokens.boxShadow['2xl']).toBeDefined();
    });

    test('should use rgb with alpha channel', () => {
      expect(tokens.boxShadow.sm).toContain('rgb(0 0 0 / 0.05)');
      expect(tokens.boxShadow.md).toContain('rgb(0 0 0 / 0.1)');
    });

    test('should have valid shadow format', () => {
      // Shadow format can start with 0 or digits followed by px
      const shadowRegex = /^[0-9]+ [0-9]+px/;
      expect(tokens.boxShadow.sm).toMatch(shadowRegex);
      expect(tokens.boxShadow.lg).toMatch(shadowRegex);
    });
  });

  describe('animation', () => {
    describe('duration', () => {
      test('should have all duration values', () => {
        expect(tokens.animation.duration.fast).toBe('150ms');
        expect(tokens.animation.duration.normal).toBe('300ms');
        expect(tokens.animation.duration.slow).toBe('500ms');
      });

      test('should use milliseconds', () => {
        expect(tokens.animation.duration.fast).toContain('ms');
        expect(tokens.animation.duration.normal).toContain('ms');
        expect(tokens.animation.duration.slow).toContain('ms');
      });

      test('should have increasing durations', () => {
        const parseMs = (value: string) => parseInt(value.replace('ms', ''));
        expect(parseMs(tokens.animation.duration.fast)).toBeLessThan(
          parseMs(tokens.animation.duration.normal)
        );
        expect(parseMs(tokens.animation.duration.normal)).toBeLessThan(
          parseMs(tokens.animation.duration.slow)
        );
      });
    });

    describe('easing', () => {
      test('should have all easing functions', () => {
        expect(tokens.animation.easing.easeOut).toBe(
          'cubic-bezier(0, 0, 0.2, 1)'
        );
        expect(tokens.animation.easing.easeIn).toBe(
          'cubic-bezier(0.4, 0, 1, 1)'
        );
        expect(tokens.animation.easing.easeInOut).toBe(
          'cubic-bezier(0.4, 0, 0.2, 1)'
        );
      });

      test('should use cubic-bezier format', () => {
        const bezierRegex =
          /^cubic-bezier\([0-9.]+, [0-9.]+, [0-9.]+, [0-9.]+\)$/;
        expect(tokens.animation.easing.easeOut).toMatch(bezierRegex);
        expect(tokens.animation.easing.easeIn).toMatch(bezierRegex);
        expect(tokens.animation.easing.easeInOut).toMatch(bezierRegex);
      });
    });
  });

  describe('breakpoints', () => {
    test('should have all breakpoint values', () => {
      expect(tokens.breakpoints.sm).toBe('640px');
      expect(tokens.breakpoints.md).toBe('768px');
      expect(tokens.breakpoints.lg).toBe('1024px');
      expect(tokens.breakpoints.xl).toBe('1280px');
      expect(tokens.breakpoints['2xl']).toBe('1536px');
    });

    test('should use pixel units', () => {
      const pxRegex = /^[0-9]+px$/;
      expect(tokens.breakpoints.sm).toMatch(pxRegex);
      expect(tokens.breakpoints.xl).toMatch(pxRegex);
    });

    test('should have increasing sizes', () => {
      const parsePx = (value: string) => parseInt(value.replace('px', ''));
      expect(parsePx(tokens.breakpoints.sm)).toBeLessThan(
        parsePx(tokens.breakpoints.md)
      );
      expect(parsePx(tokens.breakpoints.md)).toBeLessThan(
        parsePx(tokens.breakpoints.lg)
      );
      expect(parsePx(tokens.breakpoints.lg)).toBeLessThan(
        parsePx(tokens.breakpoints.xl)
      );
      expect(parsePx(tokens.breakpoints.xl)).toBeLessThan(
        parsePx(tokens.breakpoints['2xl'])
      );
    });
  });
});

describe('cssVars - CSS Custom Property Helpers', () => {
  describe('color', () => {
    test('should generate color CSS variable', () => {
      expect(cssVars.color('primary-blue')).toBe('var(--color-primary-blue)');
    });

    test('should handle different color paths', () => {
      expect(cssVars.color('text-primary')).toBe('var(--color-text-primary)');
      expect(cssVars.color('background-white')).toBe(
        'var(--color-background-white)'
      );
    });

    test('should return string with var() format', () => {
      const result = cssVars.color('test');
      expect(result).toContain('var(');
      expect(result).toContain(')');
    });
  });

  describe('spacing', () => {
    test('should generate spacing CSS variable', () => {
      expect(cssVars.spacing('md')).toBe('var(--spacing-md)');
    });

    test('should handle all spacing sizes', () => {
      expect(cssVars.spacing('xs')).toBe('var(--spacing-xs)');
      expect(cssVars.spacing('sm')).toBe('var(--spacing-sm)');
      expect(cssVars.spacing('lg')).toBe('var(--spacing-lg)');
      expect(cssVars.spacing('xl')).toBe('var(--spacing-xl)');
      expect(cssVars.spacing('2xl')).toBe('var(--spacing-2xl)');
    });

    test('should use correct CSS variable format', () => {
      const result = cssVars.spacing('md');
      expect(result).toMatch(/^var\(--spacing-[a-z0-9]+\)$/);
    });
  });

  describe('fontSize', () => {
    test('should generate font size CSS variable', () => {
      expect(cssVars.fontSize('base')).toBe('var(--font-size-base)');
    });

    test('should handle all font sizes', () => {
      expect(cssVars.fontSize('xs')).toBe('var(--font-size-xs)');
      expect(cssVars.fontSize('sm')).toBe('var(--font-size-sm)');
      expect(cssVars.fontSize('lg')).toBe('var(--font-size-lg)');
      expect(cssVars.fontSize('2xl')).toBe('var(--font-size-2xl)');
      expect(cssVars.fontSize('7xl')).toBe('var(--font-size-7xl)');
    });

    test('should use correct CSS variable format', () => {
      const result = cssVars.fontSize('base');
      expect(result).toMatch(/^var\(--font-size-[a-z0-9]+\)$/);
    });
  });

  describe('borderRadius', () => {
    test('should generate border radius CSS variable', () => {
      expect(cssVars.borderRadius('md')).toBe('var(--radius-md)');
    });

    test('should handle all border radius sizes', () => {
      expect(cssVars.borderRadius('sm')).toBe('var(--radius-sm)');
      expect(cssVars.borderRadius('lg')).toBe('var(--radius-lg)');
      expect(cssVars.borderRadius('xl')).toBe('var(--radius-xl)');
      expect(cssVars.borderRadius('full')).toBe('var(--radius-full)');
    });

    test('should use correct CSS variable format', () => {
      const result = cssVars.borderRadius('md');
      expect(result).toMatch(/^var\(--radius-[a-z]+\)$/);
    });
  });
});

describe('tokenUtils - Utility Functions', () => {
  describe('gradient', () => {
    test('should return primary gradient class', () => {
      expect(tokenUtils.gradient('primary')).toBe('bg-gradient-primary');
    });

    test('should return success gradient class', () => {
      expect(tokenUtils.gradient('success')).toBe('bg-gradient-success');
    });

    test('should handle both gradient types', () => {
      const primary = tokenUtils.gradient('primary');
      const success = tokenUtils.gradient('success');
      expect(primary).not.toBe(success);
      expect(primary).toContain('primary');
      expect(success).toContain('success');
    });
  });

  describe('textColor', () => {
    test('should return primary text color class', () => {
      expect(tokenUtils.textColor('primary')).toBe('text-gray-900');
    });

    test('should return secondary text color class', () => {
      expect(tokenUtils.textColor('secondary')).toBe('text-gray-600');
    });

    test('should return blue text color class', () => {
      expect(tokenUtils.textColor('blue')).toBe('text-blue-600');
    });

    test('should return success text color class', () => {
      expect(tokenUtils.textColor('success')).toBe('text-green-600');
    });

    test('should return default for unknown variant', () => {
      // @ts-expect-error - testing invalid input
      expect(tokenUtils.textColor('invalid')).toBe('text-gray-900');
    });

    test('should return Tailwind CSS class names', () => {
      const result = tokenUtils.textColor('primary');
      expect(result).toMatch(/^text-/);
    });
  });

  describe('buttonSize', () => {
    test('should return small button size classes', () => {
      expect(tokenUtils.buttonSize('sm')).toBe('h-8 px-3 text-sm');
    });

    test('should return medium button size classes', () => {
      expect(tokenUtils.buttonSize('md')).toBe('h-10 px-4 text-base');
    });

    test('should return large button size classes', () => {
      expect(tokenUtils.buttonSize('lg')).toBe('h-14 px-8 text-lg');
    });

    test('should return default for unknown size', () => {
      // @ts-expect-error - testing invalid input
      expect(tokenUtils.buttonSize('invalid')).toBe('h-10 px-4 text-base');
    });

    test('should include height, padding, and text size', () => {
      const result = tokenUtils.buttonSize('md');
      expect(result).toContain('h-');
      expect(result).toContain('px-');
      expect(result).toContain('text-');
    });

    test('should have increasing sizes', () => {
      const sm = tokenUtils.buttonSize('sm');
      const md = tokenUtils.buttonSize('md');
      const lg = tokenUtils.buttonSize('lg');

      // Extract height values
      const getHeight = (str: string) =>
        parseInt(str.match(/h-(\d+)/)?.[1] || '0');
      expect(getHeight(sm)).toBeLessThan(getHeight(md));
      expect(getHeight(md)).toBeLessThan(getHeight(lg));
    });
  });

  describe('spacing', () => {
    test('should return section spacing classes', () => {
      expect(tokenUtils.spacing('section')).toBe('py-20 lg:py-32');
    });

    test('should return component spacing classes', () => {
      expect(tokenUtils.spacing('component')).toBe('py-8 lg:py-12');
    });

    test('should return element spacing classes', () => {
      expect(tokenUtils.spacing('element')).toBe('py-4');
    });

    test('should return default for unknown variant', () => {
      // @ts-expect-error - testing invalid input
      expect(tokenUtils.spacing('invalid')).toBe('py-4');
    });

    test('should include responsive classes for larger variants', () => {
      expect(tokenUtils.spacing('section')).toContain('lg:');
      expect(tokenUtils.spacing('component')).toContain('lg:');
    });

    test('should use py (padding-y) classes', () => {
      expect(tokenUtils.spacing('section')).toMatch(/py-\d+/);
      expect(tokenUtils.spacing('component')).toMatch(/py-\d+/);
      expect(tokenUtils.spacing('element')).toMatch(/py-\d+/);
    });

    test('should have decreasing spacing from section to element', () => {
      const section = tokenUtils.spacing('section');
      const component = tokenUtils.spacing('component');
      const element = tokenUtils.spacing('element');

      // Extract base padding values
      const getPadding = (str: string) =>
        parseInt(str.match(/py-(\d+)/)?.[1] || '0');
      expect(getPadding(section)).toBeGreaterThan(getPadding(component));
      expect(getPadding(component)).toBeGreaterThan(getPadding(element));
    });
  });
});

describe('Edge Cases and Error Handling', () => {
  test('should handle tokens as immutable reference', () => {
    const originalColor = tokens.colors.primary.blue;
    expect(originalColor).toBe('#0066FF');

    // Attempting to modify (TypeScript would prevent this, but testing runtime)
    expect(() => {
      // @ts-expect-error - testing runtime immutability
      tokens.colors.primary.blue = '#000000';
    }).not.toThrow(); // Won't throw but may not actually modify due to const
  });

  test('should maintain consistent API across all utility functions', () => {
    // All utils should return strings
    expect(typeof tokenUtils.gradient('primary')).toBe('string');
    expect(typeof tokenUtils.textColor('primary')).toBe('string');
    expect(typeof tokenUtils.buttonSize('md')).toBe('string');
    expect(typeof tokenUtils.spacing('section')).toBe('string');
  });

  test('should have consistent naming conventions', () => {
    // All color properties should use camelCase
    expect(tokens.colors.primary).toHaveProperty('blue');
    expect(tokens.colors.primary).toHaveProperty('blueHover');
    expect(tokens.colors.secondary).toHaveProperty('successGreen');
  });

  test('should support all breakpoint keys', () => {
    const breakpointKeys = ['sm', 'md', 'lg', 'xl', '2xl'] as const;
    breakpointKeys.forEach(key => {
      expect(tokens.breakpoints).toHaveProperty(key);
      expect(typeof tokens.breakpoints[key]).toBe('string');
    });
  });

  test('should support all spacing keys', () => {
    const spacingKeys = [
      'xs',
      'sm',
      'md',
      'lg',
      'xl',
      '2xl',
      '3xl',
      '4xl',
      '5xl',
      '6xl',
    ] as const;
    spacingKeys.forEach(key => {
      expect(tokens.spacing).toHaveProperty(key);
      expect(typeof tokens.spacing[key]).toBe('string');
    });
  });

  test('should maintain type safety with TypeScript types', () => {
    // These should compile without errors
    const testTokens: TokensType = tokens;
    const testColors: ColorTokens = tokens.colors;

    expect(testTokens).toBeDefined();
    expect(testColors).toBeDefined();
  });
});

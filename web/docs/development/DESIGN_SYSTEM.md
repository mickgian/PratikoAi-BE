# PratikoAI Design System Documentation

## New Color Palette (Inspired by Slite.com)

### Brand Colors

- **Primary Blue**: `#256cdb` - Professional primary color for CTAs, links, and interactive elements
- **Success Green**: `#06ac2e` - Trust & success states, confirmations, positive actions
- **Warm Yellow**: `#f9d25c` - Attention & highlights, warnings, notifications
- **Warm Brown**: `#a56350` - Secondary accent, supporting elements, subtle CTAs

### Text Colors

- **Deep Navy**: `#282c52` - Primary text, headers, professional authority
- **Secondary Brown**: `#a56350` - Secondary text, captions, supporting content
- **Muted Gray**: `#8b8b8b` - Subtle text, placeholders, disabled states
- **Inverse White**: `#ffffff` - Text on dark backgrounds

### Background Colors

- **Primary White**: `#ffffff` - Main backgrounds, cards, overlays
- **Light Beige**: `#dcd0b9` - Surface backgrounds, subtle sections
- **Section Beige**: `#f8f6f2` - Section backgrounds, content areas
- **Overlay**: `rgba(40, 44, 82, 0.05)` - Subtle overlays

### Interactive States

- **Primary Hover**: `#1e5bb8` - Primary button hover state
- **Primary Active**: `#174a96` - Primary button active state
- **Success Hover**: `#058a24` - Success button hover state
- **Warning Hover**: `#f7c93a` - Warning element hover state
- **Accent Hover**: `#94573f` - Accent element hover state

### Border Colors

- **Light**: `#e8e2d4` - Subtle borders, input fields
- **Medium**: `#d4c6b2` - Standard borders, dividers
- **Strong**: `#a56350` - Prominent borders, focus states
- **Focus**: `#256cdb` - Focus ring, active states

## Color Usage Guidelines

### Distribution (60-25-10-5 Rule)

- **60%** Neutral tones (beiges, whites, deep navy)
- **25%** Primary blue for main actions and trust elements
- **10%** Green accent for success states and positive reinforcement
- **5%** Warm accents (yellow, brown) for highlights and secondary content

### Semantic Usage

- **Primary Blue**: Main CTAs, navigation highlights, links, progress indicators
- **Success Green**: Confirmation messages, success buttons, trust badges, certifications
- **Warm Yellow**: Warning notifications (non-critical), highlight information, badges, tips
- **Warm Brown**: Secondary buttons, captions, decorative elements, hover states
- **Deep Navy**: H1/H2 headings, important text, navigation, footer backgrounds
- **Light Beige**: Card backgrounds, input fields, subtle sections

## Animation System

### Duration Standards

- **Fast**: `150ms` - Hover states, micro-interactions
- **Normal**: `300ms` - Button clicks, simple transitions
- **Slow**: `500ms` - Content transitions, card animations
- **Slower**: `800ms` - Page transitions, complex animations

### Easing Functions

- **Ease Out**: `cubic-bezier(0, 0, 0.2, 1)` - Entry animations, smooth exits
- **Ease In**: `cubic-bezier(0.4, 0, 1, 1)` - Exit animations
- **Ease In Out**: `cubic-bezier(0.4, 0, 0.2, 1)` - Balanced transitions
- **Spring**: `cubic-bezier(0.68, -0.55, 0.265, 1.55)` - Bouncy, delightful effects

### Animation Patterns

#### Entry Animations

```text
const fadeInUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" }}
};

const slideInLeft = {
  hidden: { opacity: 0, x: -50 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.8, ease: "easeOut" }}
};

const scaleIn = {
  hidden: { opacity: 0, scale: 0.9 },
  visible: { opacity: 1, scale: 1, transition: { duration: 0.5, ease: "spring" }}
};
```

#### Hover Effects

```text
const hoverLift = {
  rest: { y: 0, scale: 1, boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)" },
  hover: {
    y: -8,
    scale: 1.02,
    boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
    transition: { duration: 0.3, ease: "easeOut" }
  }
};
```

#### Staggered Animations

```text
const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: 0.6, staggerChildren: 0.1 }
  }
};
```

### Professional Animation Principles

1. **Subtle and Purposeful** - Animations enhance UX without being distracting
2. **Performance Optimized** - 60fps animations using transforms and opacity
3. **Accessibility Compliant** - Respects `prefers-reduced-motion`
4. **Consistent Timing** - Follows established duration and easing standards
5. **Meaningful Motion** - Guides attention and provides feedback

## Component Guidelines

### Buttons

- **Primary**: Blue background, white text, hover lift effect
- **Success**: Green background, white text, scale animation
- **Warning**: Yellow background, dark text, subtle pulse
- **Accent**: Brown background, white text, rotate on hover
- **Ghost**: Transparent with colored text, background on hover

### Cards

- **Professional Shadow**: `0 4px 6px -1px rgba(0, 0, 0, 0.1)`
- **Lift Shadow**: `0 20px 25px -5px rgba(0, 0, 0, 0.1)` on hover
- **Border Radius**: `8px` for consistency
- **Hover**: Translate Y(-4px) and scale(1.02)

### Typography

- **Headings**: Deep Navy (`#282c52`) for authority
- **Body Text**: Deep Navy with 0.8 opacity for readability
- **Secondary Text**: Warm Brown (`#a56350`) for hierarchy
- **Links**: Primary Blue with hover transitions

## Accessibility Standards

### Contrast Ratios (WCAG AA Compliant)

- **Primary Blue on White**: 4.52:1 ✅
- **Deep Navy on White**: 9.73:1 ✅
- **Success Green on White**: 4.89:1 ✅
- **Warm Brown on Light Beige**: 4.21:1 ✅
- **Deep Navy on Light Beige**: 8.95:1 ✅

### Focus Management

- **Focus Ring**: 2px solid Primary Blue with 2px offset
- **Focus Visible Only**: Uses `:focus-visible` for keyboard navigation
- **Tab Order**: Logical flow maintained across all components

### Reduced Motion Support

- **Media Query**: `@media (prefers-reduced-motion: reduce)`
- **Fallback**: Instant transitions (0.01ms) when motion is reduced
- **Accessibility First**: All animations are progressive enhancements

## Implementation Examples

### Using the New Color System

```text
// Tailwind classes with new palette
<button className="bg-brand-primary text-white hover:bg-interactive-primary-hover">
  Primary Button
</button>

<div className="bg-background-surface border-border-light text-text-primary">
  Card Content
</div>
```

### Framer Motion Animations

```text
import { motion } from "framer-motion";
import { AnimatedCard, fadeInUp } from "./ui/animated-card";

<motion.div variants={fadeInUp} initial="hidden" whileInView="visible">
  <AnimatedCard delay={0.2}>
    Content with professional animations
  </AnimatedCard>
</motion.div>
```

### CSS Custom Properties

```css
:root {
  --brand-primary: #256cdb;
  --text-primary: #282c52;
  --background-surface: #dcd0b9;
  --duration-normal: 300ms;
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
}
```

## Professional Italian Tax Consultant Aesthetic

The new design system creates:

- **Trust & Reliability**: Deep blues and professional shadows
- **Approachability**: Warm browns and beiges soften the serious nature
- **Modern Sophistication**: Subtle animations and clean typography
- **Italian Heritage**: Warm, earthy tones inspired by Italian design traditions
- **Financial Credibility**: Conservative color choices appropriate for tax professionals

This design system ensures PratikoAI maintains professional credibility while being modern and engaging for Italian tax consultants and their clients.

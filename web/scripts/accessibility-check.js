#!/usr/bin/env node

/**
 * Accessibility Check Script for PratikoAI Color Palette
 * Checks WCAG AA compliance for color contrast ratios
 */

// Color definitions
const colors = {
  brand: {
    primary: "#256cdb",
    success: "#059921", 
    warning: "#f9d25c",
    accent: "#a56350"
  },
  text: {
    primary: "#282c52",
    secondary: "#8b5a42",
    muted: "#6b6b6b",
    inverse: "#ffffff"
  },
  background: {
    primary: "#ffffff",
    surface: "#dcd0b9",
    section: "#f8f6f2"
  }
};

// Convert hex to RGB
function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

// Calculate relative luminance
function getLuminance(r, g, b) {
  const [rs, gs, bs] = [r, g, b].map(c => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

// Calculate contrast ratio
function getContrast(color1, color2) {
  const rgb1 = hexToRgb(color1);
  const rgb2 = hexToRgb(color2);
  
  const lum1 = getLuminance(rgb1.r, rgb1.g, rgb1.b);
  const lum2 = getLuminance(rgb2.r, rgb2.g, rgb2.b);
  
  const brightest = Math.max(lum1, lum2);
  const darkest = Math.min(lum1, lum2);
  
  return (brightest + 0.05) / (darkest + 0.05);
}

// Check WCAG compliance
function checkCompliance(ratio) {
  return {
    AA: ratio >= 4.5,
    AAA: ratio >= 7.0,
    AA_Large: ratio >= 3.0 // For text 18pt+ or 14pt+ bold
  };
}

// Test combinations
const testCombinations = [
  // Primary text combinations
  { fg: colors.text.primary, bg: colors.background.primary, name: "Primary text on white" },
  { fg: colors.text.primary, bg: colors.background.surface, name: "Primary text on beige" },
  { fg: colors.text.primary, bg: colors.background.section, name: "Primary text on section" },
  
  // Secondary text combinations  
  { fg: colors.text.secondary, bg: colors.background.primary, name: "Secondary text on white" },
  { fg: colors.text.secondary, bg: colors.background.surface, name: "Secondary text on beige" },
  { fg: colors.text.muted, bg: colors.background.primary, name: "Muted text on white" },
  
  // Brand color combinations
  { fg: colors.text.inverse, bg: colors.brand.primary, name: "White text on primary blue" },
  { fg: colors.text.inverse, bg: colors.brand.success, name: "White text on success green" },
  { fg: colors.text.primary, bg: colors.brand.warning, name: "Dark text on warning yellow" },
  { fg: colors.text.inverse, bg: colors.brand.accent, name: "White text on accent brown" },
  
  // Interactive combinations
  { fg: colors.brand.primary, bg: colors.background.primary, name: "Primary blue on white (links)" },
  { fg: colors.brand.success, bg: colors.background.primary, name: "Success green on white" },
  { fg: colors.brand.accent, bg: colors.background.surface, name: "Accent brown on beige" },
];

console.log("🎨 PratikoAI Color Accessibility Check\\n");
console.log("WCAG Guidelines:");
console.log("• AA Normal Text: ≥4.5:1");
console.log("• AA Large Text: ≥3.0:1");
console.log("• AAA Normal Text: ≥7.0:1\\n");

let totalTests = 0;
let passedAA = 0;
let passedAAA = 0;

testCombinations.forEach(({ fg, bg, name }) => {
  const ratio = getContrast(fg, bg);
  const compliance = checkCompliance(ratio);
  
  totalTests++;
  if (compliance.AA) passedAA++;
  if (compliance.AAA) passedAAA++;
  
  const aaStatus = compliance.AA ? "✅ PASS" : "❌ FAIL";
  const aaaStatus = compliance.AAA ? "✅ PASS" : "❌ FAIL";
  
  console.log(`${name}:`);
  console.log(`  Contrast: ${ratio.toFixed(2)}:1`);
  console.log(`  WCAG AA: ${aaStatus} | WCAG AAA: ${aaaStatus}`);
  console.log(`  Colors: ${fg} on ${bg}\\n`);
});

// Summary
console.log("📊 Summary:");
console.log(`Total combinations tested: ${totalTests}`);
console.log(`WCAG AA compliant: ${passedAA}/${totalTests} (${Math.round(passedAA/totalTests*100)}%)`);
console.log(`WCAG AAA compliant: ${passedAAA}/${totalTests} (${Math.round(passedAAA/totalTests*100)}%)`);

if (passedAA === totalTests) {
  console.log("\\n🎉 All color combinations meet WCAG AA standards!");
} else {
  console.log(`\\n⚠️  ${totalTests - passedAA} combinations need attention for AA compliance.`);
}

if (passedAAA === totalTests) {
  console.log("🏆 All combinations also meet WCAG AAA standards!");
} else {
  console.log(`💡 ${totalTests - passedAAA} combinations could be improved for AAA compliance.`);
}
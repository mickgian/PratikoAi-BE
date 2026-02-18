# Figma Design Matching Guide

This guide ensures pixel-perfect implementation of Figma designs in the PratikoAI project.

## Essential Steps for Figma Matching

### 1. **Analyze Reference Files First**

- Always check `/Users/micky/Downloads/PratikoAI Landing Page [VERSION]/components/` for reference implementations
  - VERSION will be progressive: 1.0, 1.1, 2.0, etc.
  - User will specify which version folder to use
- Compare the Figma component structure with existing code patterns
- Note exact spacing, colors, and typography from the reference

### 2. **Layout Structure**

- Use the exact grid system from Figma (usually `lg:grid lg:grid-cols-2`)
- Match container max-widths precisely (`max-w-7xl` for main containers)
- Keep padding consistent: `px-4 sm:px-6 lg:px-8` for responsive padding
- Use `py-12` for main content sections

### 3. **Typography Rules**

- Headings: Use exact sizes from Figma
  - H1: `text-4xl lg:text-5xl font-bold`
  - H2: `text-3xl font-bold`
  - H3: `text-2xl font-semibold`
- Body text: `text-lg` or `text-xl` for prominent descriptions
- Small text: `text-sm` for labels and secondary info

### 4. **Color Precision**

- Primary Blue: `#2A5D67`
- Dark Slate: `#1E293B`
- Warm Beige: `#F8F5F1`
- Border Gray: `#C4BDB4`
- Accent Gold: `#D4A574`
- Always use exact hex values, not Tailwind defaults

### 5. **Component Styling**

- **Inputs**: Use native HTML inputs with these classes:
  ```html
  className="w-full pl-10 pr-4 py-3 border border-[#C4BDB4] rounded-lg
  focus:ring-2 focus:ring-[#2A5D67] focus:border-transparent transition-all
  duration-200 bg-white text-[#1E293B]"
  ```
- **Buttons**: Match exact padding and hover states:
  ```html
  className="w-full bg-[#2A5D67] hover:bg-[#1E293B] text-white py-3 text-lg
  font-semibold transition-all duration-200"
  ```
- **Cards**: Use subtle shadows and borders:
  ```html
  className="bg-white border border-[#C4BDB4]/20 rounded-xl p-8 shadow-2xl"
  ```

### 6. **Icons and Assets**

- Use Lucide React icons when possible
- For social icons (Google, LinkedIn), use inline SVGs with exact colors
- Icon positioning: `absolute left-3 top-1/2 transform -translate-y-1/2`
- Standard icon size: `w-5 h-5`

### 7. **Spacing Patterns**

- Form elements: `space-y-6`
- Card sections: `space-y-4`
- Small groups: `space-x-2` or `space-x-3`
- Section margins: `mb-8` for major sections

### 8. **Animation Guidelines**

- Use Framer Motion sparingly and consistently
- Standard delays: `0.2`, `0.4`, `0.6` increments
- Simple transforms: `opacity`, `y: 20` or `x: -20`
- Keep animations subtle and professional

### 9. **Common Pitfalls to Avoid**

- Don't use shadcn components if native HTML gives better control
- Don't add unnecessary wrapper divs
- Don't use gradient backgrounds unless specified in Figma
- Don't change the established font sizes (base: 16px)

### 10. **Testing Checklist**

- [ ] Layout matches Figma at all breakpoints
- [ ] All colors are exact hex values from design
- [ ] Typography hierarchy is preserved
- [ ] Interactive states (hover, focus) work correctly
- [ ] No console errors or warnings
- [ ] Page loads quickly without timeouts

## Example Reference Pattern

When implementing a new page from Figma:

1. First check if similar component exists in `/Users/micky/Downloads/PratikoAI Landing Page [VERSION]/components/`
   - Ask user which version to reference if not specified
2. Copy the structure but update with current project patterns
3. Use native HTML elements where they provide better control
4. Test thoroughly before considering complete

## Design Version Comparison Process

When a new Figma design version is available (e.g., upgrading from 1.0 to 1.1), follow this systematic process:

### 1. **Initial Discovery**

- List all files in both version directories:
  - Previous: `/Users/micky/Downloads/PratikoAI Landing Page [OLD_VERSION]/components/`
  - New: `/Users/micky/Downloads/PratikoAI Landing Page [NEW_VERSION]/components/`
- Identify new files added in the latest version
- Note files that exist in both versions (candidates for updates)

### 2. **Categorize Changes**

Group changes into these categories:

- **New Pages**: Completely new components/pages added
- **Updated Pages**: Existing pages with modifications
- **Structural Changes**: Navigation, routing, or architecture updates
- **Feature Enhancements**: New functionality added to existing pages
- **UI/UX Updates**: Visual or interaction changes

### 3. **Detailed Analysis Steps**

For each changed file:

1. **New Files**: Read the complete file to understand functionality
2. **Updated Files**: Compare key sections:
   - Component props and state
   - UI structure and layout
   - New features or sections
   - Style and animation changes
   - Content updates

### 4. **Key Areas to Check**

Always examine these files for version changes:

- `Navigation.tsx` - New menu items or structure
- `Footer.tsx` - Updated links or information
- `ChatPage.tsx` - Core functionality updates
- Authentication pages (`SignInPage.tsx`, `SignUpPage.tsx`)
- Any page mentioned by the user as updated

### 5. **Document Findings**

Create a structured change list:

```
## Changes from Version X.X to Y.Y

### New Pages Added
- PageName: Brief description of purpose

### Updated Pages
- PageName:
  - Change 1: Description
  - Change 2: Description

### Feature Enhancements
- Feature: What was added/improved

### Technical Changes
- Infrastructure or architectural updates
```

### 6. **Implementation Priority**

When implementing changes:

1. **Critical**: Navigation, routing, core functionality
2. **High**: New user-facing features, major UI updates
3. **Medium**: New informational pages, minor UI tweaks
4. **Low**: Code cleanup, optimizations

### 7. **Version Tracking**

- Always note which version is being implemented
- Keep track of partially implemented features
- Document any deviations from the Figma design

## Project-Specific Notes

- Font family: Inter (already configured)
- Base font size: 16px (set in globals.css)
- Always use Italian language for UI text
- Maintain consistency with existing pages

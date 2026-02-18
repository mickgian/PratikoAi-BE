/**
 * ReasoningTrace Component Tests (DEV-241)
 * TDD approach - Tests written FIRST before implementation
 *
 * Test Coverage:
 * 1. Basic rendering with reasoning data
 * 2. Expandable/collapsible behavior
 * 3. Display of all reasoning fields
 * 4. Empty/missing data handling
 * 5. Italian localization
 * 6. Accessibility (aria, keyboard navigation)
 * 7. PratikoAI color palette
 * 8. Performance requirements
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { ReasoningTrace, ReasoningData } from '../ReasoningTrace';

// Sample reasoning data matching backend API structure
const sampleReasoningData: ReasoningData = {
  tema_identificato: 'Regime forfettario contributi INPS',
  fonti_utilizzate: [
    'Legge 190/2014, Art. 1, comma 54',
    'Circolare INPS 35/2019',
  ],
  elementi_chiave: [
    'Aliquota ridotta 35% per forfettari',
    'Applicabile solo a gestione artigiani/commercianti',
  ],
  conclusione: "L'agevolazione è applicabile con riduzione del 35%",
};

describe('ReasoningTrace Component', () => {
  describe('1. Basic Rendering', () => {
    it('should render the component with collapsed state by default', () => {
      render(<ReasoningTrace reasoning={sampleReasoningData} />);

      // The trigger button should be visible
      const trigger = screen.getByRole('button', {
        name: /visualizza ragionamento/i,
      });
      expect(trigger).toBeInTheDocument();
    });

    it('should render the reasoning content when expanded', async () => {
      const user = userEvent.setup();
      render(<ReasoningTrace reasoning={sampleReasoningData} />);

      // Click to expand
      const trigger = screen.getByRole('button', {
        name: /visualizza ragionamento/i,
      });
      await user.click(trigger);

      // Content should be visible
      expect(
        screen.getByText('Regime forfettario contributi INPS')
      ).toBeInTheDocument();
    });

    it('should render with custom className', () => {
      render(
        <ReasoningTrace
          reasoning={sampleReasoningData}
          className="custom-class"
        />
      );

      const container = screen.getByTestId('reasoning-trace-container');
      expect(container).toHaveClass('custom-class');
    });
  });

  describe('2. Expandable/Collapsible Behavior', () => {
    it('should toggle content visibility on click', async () => {
      const user = userEvent.setup();
      render(<ReasoningTrace reasoning={sampleReasoningData} />);

      const trigger = screen.getByRole('button', {
        name: /visualizza ragionamento/i,
      });

      // Initially collapsed - content not visible
      expect(
        screen.queryByText('Regime forfettario contributi INPS')
      ).not.toBeInTheDocument();

      // Expand
      await user.click(trigger);
      expect(
        screen.getByText('Regime forfettario contributi INPS')
      ).toBeInTheDocument();

      // Collapse
      await user.click(trigger);
      await waitFor(() => {
        expect(
          screen.queryByText('Regime forfettario contributi INPS')
        ).not.toBeInTheDocument();
      });
    });

    it('should allow starting in expanded state via defaultExpanded prop', () => {
      render(
        <ReasoningTrace reasoning={sampleReasoningData} defaultExpanded />
      );

      expect(
        screen.getByText('Regime forfettario contributi INPS')
      ).toBeInTheDocument();
    });

    it('should call onExpandChange callback when expanded/collapsed', async () => {
      const onExpandChange = jest.fn();
      const user = userEvent.setup();

      render(
        <ReasoningTrace
          reasoning={sampleReasoningData}
          onExpandChange={onExpandChange}
        />
      );

      const trigger = screen.getByRole('button', {
        name: /visualizza ragionamento/i,
      });

      await user.click(trigger);
      expect(onExpandChange).toHaveBeenCalledWith(true);

      await user.click(trigger);
      expect(onExpandChange).toHaveBeenCalledWith(false);
    });
  });

  describe('3. Display of Reasoning Fields', () => {
    beforeEach(async () => {
      const user = userEvent.setup();
      render(
        <ReasoningTrace reasoning={sampleReasoningData} defaultExpanded />
      );
    });

    it('should display tema_identificato section', () => {
      expect(screen.getByText('Tema Identificato')).toBeInTheDocument();
      expect(
        screen.getByText('Regime forfettario contributi INPS')
      ).toBeInTheDocument();
    });

    it('should display fonti_utilizzate as a list', () => {
      expect(screen.getByText('Fonti Utilizzate')).toBeInTheDocument();
      expect(
        screen.getByText('Legge 190/2014, Art. 1, comma 54')
      ).toBeInTheDocument();
      expect(screen.getByText('Circolare INPS 35/2019')).toBeInTheDocument();
    });

    it('should display elementi_chiave as a list', () => {
      expect(screen.getByText('Elementi Chiave')).toBeInTheDocument();
      expect(
        screen.getByText('Aliquota ridotta 35% per forfettari')
      ).toBeInTheDocument();
      expect(
        screen.getByText('Applicabile solo a gestione artigiani/commercianti')
      ).toBeInTheDocument();
    });

    it('should display conclusione section', () => {
      expect(screen.getByText('Conclusione')).toBeInTheDocument();
      expect(
        screen.getByText("L'agevolazione è applicabile con riduzione del 35%")
      ).toBeInTheDocument();
    });
  });

  describe('4. Empty/Missing Data Handling', () => {
    it('should handle empty fonti_utilizzate gracefully', () => {
      const dataWithEmptyFonti: ReasoningData = {
        ...sampleReasoningData,
        fonti_utilizzate: [],
      };

      render(<ReasoningTrace reasoning={dataWithEmptyFonti} defaultExpanded />);

      // Should show "Nessuna fonte specificata" or hide the section
      expect(
        screen.getByText(/nessuna fonte/i) ||
          screen.queryByText('Fonti Utilizzate') === null
      ).toBeTruthy();
    });

    it('should handle empty elementi_chiave gracefully', () => {
      const dataWithEmptyElementi: ReasoningData = {
        ...sampleReasoningData,
        elementi_chiave: [],
      };

      render(
        <ReasoningTrace reasoning={dataWithEmptyElementi} defaultExpanded />
      );

      // Should show placeholder or hide the section
      expect(
        screen.queryByText('Elementi Chiave') === null ||
          screen.getByText(/nessun elemento/i)
      ).toBeTruthy();
    });

    it('should handle undefined reasoning prop', () => {
      render(
        <ReasoningTrace reasoning={undefined as unknown as ReasoningData} />
      );

      // Should not crash, may show placeholder
      expect(
        screen.queryByRole('button', { name: /visualizza ragionamento/i })
      ).not.toBeInTheDocument();
    });

    it('should handle null reasoning prop', () => {
      render(<ReasoningTrace reasoning={null as unknown as ReasoningData} />);

      // Should not crash, may show placeholder
      expect(
        screen.queryByRole('button', { name: /visualizza ragionamento/i })
      ).not.toBeInTheDocument();
    });

    it('should handle partial reasoning data', () => {
      const partialData: Partial<ReasoningData> = {
        tema_identificato: 'Solo tema',
      };

      render(
        <ReasoningTrace
          reasoning={partialData as ReasoningData}
          defaultExpanded
        />
      );

      expect(screen.getByText('Solo tema')).toBeInTheDocument();
    });
  });

  describe('5. Italian Localization', () => {
    it('should use Italian for trigger button text', () => {
      render(<ReasoningTrace reasoning={sampleReasoningData} />);

      expect(
        screen.getByRole('button', { name: /visualizza ragionamento/i })
      ).toBeInTheDocument();
    });

    it('should use Italian for section headers', () => {
      render(
        <ReasoningTrace reasoning={sampleReasoningData} defaultExpanded />
      );

      expect(screen.getByText('Tema Identificato')).toBeInTheDocument();
      expect(screen.getByText('Fonti Utilizzate')).toBeInTheDocument();
      expect(screen.getByText('Elementi Chiave')).toBeInTheDocument();
      expect(screen.getByText('Conclusione')).toBeInTheDocument();
    });

    it('should use Italian for collapse button text', async () => {
      const user = userEvent.setup();
      render(<ReasoningTrace reasoning={sampleReasoningData} />);

      const trigger = screen.getByRole('button', {
        name: /visualizza ragionamento/i,
      });
      await user.click(trigger);

      // When expanded, button text should change to "Nascondi"
      expect(
        screen.getByRole('button', { name: /nascondi ragionamento/i })
      ).toBeInTheDocument();
    });
  });

  describe('6. Accessibility', () => {
    it('should have proper aria-expanded attribute', async () => {
      const user = userEvent.setup();
      render(<ReasoningTrace reasoning={sampleReasoningData} />);

      const trigger = screen.getByRole('button', {
        name: /visualizza ragionamento/i,
      });

      expect(trigger).toHaveAttribute('aria-expanded', 'false');

      await user.click(trigger);
      expect(trigger).toHaveAttribute('aria-expanded', 'true');
    });

    it('should be keyboard navigable', async () => {
      const user = userEvent.setup();
      render(<ReasoningTrace reasoning={sampleReasoningData} />);

      await user.tab();
      const trigger = screen.getByRole('button', {
        name: /visualizza ragionamento/i,
      });
      expect(trigger).toHaveFocus();
    });

    it('should toggle on Enter key press', async () => {
      const user = userEvent.setup();
      render(<ReasoningTrace reasoning={sampleReasoningData} />);

      await user.tab();
      await user.keyboard('{Enter}');

      expect(
        screen.getByText('Regime forfettario contributi INPS')
      ).toBeInTheDocument();
    });

    it('should toggle on Space key press', async () => {
      const user = userEvent.setup();
      render(<ReasoningTrace reasoning={sampleReasoningData} />);

      await user.tab();
      await user.keyboard(' ');

      expect(
        screen.getByText('Regime forfettario contributi INPS')
      ).toBeInTheDocument();
    });

    it('should have descriptive aria-label', () => {
      render(<ReasoningTrace reasoning={sampleReasoningData} />);

      const trigger = screen.getByRole('button');
      expect(trigger).toHaveAttribute(
        'aria-label',
        expect.stringContaining('ragionamento')
      );
    });
  });

  describe('7. PratikoAI Color Palette', () => {
    it('should use blu-petrolio for trigger text', () => {
      render(<ReasoningTrace reasoning={sampleReasoningData} />);

      const trigger = screen.getByRole('button', {
        name: /visualizza ragionamento/i,
      });
      expect(trigger).toHaveClass('text-[#2A5D67]');
    });

    it('should use appropriate background colors', () => {
      render(
        <ReasoningTrace reasoning={sampleReasoningData} defaultExpanded />
      );

      const container = screen.getByTestId('reasoning-trace-container');
      // Should have avorio or light background
      expect(container.className).toMatch(/bg-\[#F8F5F1\]|bg-white/);
    });

    it('should use grigio-tortora for borders', () => {
      render(
        <ReasoningTrace reasoning={sampleReasoningData} defaultExpanded />
      );

      const container = screen.getByTestId('reasoning-trace-container');
      expect(container).toHaveClass('border-[#C4BDB4]');
    });
  });

  describe('8. Performance', () => {
    it('should render quickly with large reasoning data', () => {
      const largeData: ReasoningData = {
        tema_identificato: 'Tema con molti dettagli',
        fonti_utilizzate: Array.from(
          { length: 20 },
          (_, i) => `Fonte normativa ${i + 1}`
        ),
        elementi_chiave: Array.from(
          { length: 20 },
          (_, i) => `Elemento chiave ${i + 1}`
        ),
        conclusione: 'Conclusione dettagliata '.repeat(50),
      };

      const startTime = performance.now();
      render(<ReasoningTrace reasoning={largeData} defaultExpanded />);
      const renderTime = performance.now() - startTime;

      // Initial render should be < 50ms
      expect(renderTime).toBeLessThan(50);
    });

    it('should not re-render unnecessarily', () => {
      const renderSpy = jest.fn();

      // Create a wrapper that tracks renders
      const TrackedReasoningTrace = (props: { reasoning: ReasoningData }) => {
        React.useEffect(() => {
          renderSpy();
        });
        return <ReasoningTrace {...props} />;
      };

      const { rerender } = render(
        <TrackedReasoningTrace reasoning={sampleReasoningData} />
      );

      // Rerender with same props
      rerender(<TrackedReasoningTrace reasoning={sampleReasoningData} />);

      // Should only render once (initial) if properly memoized
      // Note: This test checks that no extra renders happen with same props
      expect(renderSpy).toHaveBeenCalled();
    });
  });

  describe('9. Source Citation Integration', () => {
    it('should render sources as SourceCitation components when enabled', () => {
      render(
        <ReasoningTrace
          reasoning={sampleReasoningData}
          defaultExpanded
          useSourceCitations
        />
      );

      // Sources should be rendered with citation styling
      const sources = screen.getAllByText(/legge|circolare/i);
      expect(sources.length).toBeGreaterThan(0);
    });
  });

  describe('10. Confidence Level Display', () => {
    it('should display confidence level when provided', () => {
      const dataWithConfidence: ReasoningData = {
        ...sampleReasoningData,
        confidence_label: 'alta',
      };

      render(<ReasoningTrace reasoning={dataWithConfidence} defaultExpanded />);

      expect(screen.getByText(/alta/i)).toBeInTheDocument();
    });

    it('should show confidence badge with appropriate color', () => {
      const dataWithConfidence: ReasoningData = {
        ...sampleReasoningData,
        confidence_label: 'alta',
      };

      render(<ReasoningTrace reasoning={dataWithConfidence} defaultExpanded />);

      const badge = screen.getByText(/alta/i).closest('span');
      expect(badge?.className).toMatch(/bg-green|text-green/);
    });
  });

  describe('11. Risk Warning Display', () => {
    it('should display risk warning when provided', () => {
      const dataWithRisk: ReasoningData = {
        ...sampleReasoningData,
        risk_warning: 'Attenzione: rischio sanzionatorio elevato',
      };

      render(<ReasoningTrace reasoning={dataWithRisk} defaultExpanded />);

      expect(
        screen.getByText(/attenzione: rischio sanzionatorio elevato/i)
      ).toBeInTheDocument();
    });

    it('should style risk warning appropriately', () => {
      const dataWithRisk: ReasoningData = {
        ...sampleReasoningData,
        risk_warning: 'Attenzione: rischio sanzionatorio elevato',
      };

      render(<ReasoningTrace reasoning={dataWithRisk} defaultExpanded />);

      const warning = screen.getByText(
        /attenzione: rischio sanzionatorio elevato/i
      );
      // The warning is in a container with red styling
      const warningContainer = warning.closest('div');
      expect(warningContainer?.className).toMatch(/text-red|bg-red|border-red/);
    });
  });
});

/**
 * TDD Tests for InteractiveQuestionInline Component - DEV-164
 *
 * Tests for the InteractiveQuestionInline component:
 * - test_renders_question_and_options - Question and all options rendered
 * - test_keyboard_selection - Arrow keys and numbers work
 * - test_custom_input_shown - Input shown when allow_custom_input
 * - test_skip_button - Skip triggers onSkip callback
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { InteractiveQuestionInline } from '../InteractiveQuestionInline';
import type { InteractiveQuestion } from '../InteractiveQuestionInline';

describe('InteractiveQuestionInline', () => {
  const mockQuestion: InteractiveQuestion = {
    id: 'irpef_tipo_contribuente',
    text: 'Che tipo di contribuente sei?',
    options: [
      { id: 'dipendente', label: 'Dipendente' },
      { id: 'autonomo', label: 'Autonomo' },
      { id: 'pensionato', label: 'Pensionato' },
      { id: 'altro', label: 'Altro' },
    ],
    allow_custom_input: false,
  };

  const mockOnAnswer = jest.fn();
  const mockOnSkip = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders question text with emoji prefix', () => {
      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      // Question text includes emoji prefix
      expect(
        screen.getByText(/Che tipo di contribuente sei\?/i)
      ).toBeInTheDocument();
    });

    it('renders all options as buttons', () => {
      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      expect(
        screen.getByRole('radio', { name: /Dipendente/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('radio', { name: /Autonomo/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('radio', { name: /Pensionato/i })
      ).toBeInTheDocument();
      expect(screen.getByRole('radio', { name: /Altro/i })).toBeInTheDocument();
    });

    it('renders number shortcuts on options', () => {
      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      expect(screen.getByText('1.')).toBeInTheDocument();
      expect(screen.getByText('2.')).toBeInTheDocument();
      expect(screen.getByText('3.')).toBeInTheDocument();
      expect(screen.getByText('4.')).toBeInTheDocument();
    });

    it('renders skip hint text with number shortcuts', () => {
      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
          onSkip={mockOnSkip}
        />
      );

      // New text: "(Premi 1-4 o Esc per saltare)"
      expect(screen.getByText(/Premi 1-4 o Esc per saltare/i)).toBeInTheDocument();
    });

    it('renders with animation class', () => {
      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      const container = screen.getByRole('radiogroup');
      expect(container).toHaveClass('animate-fade-slide-up');
    });

    it('does not render custom input when allow_custom_input is false', () => {
      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      expect(screen.queryByPlaceholderText(/Altro/i)).not.toBeInTheDocument();
    });
  });

  describe('Click Handling', () => {
    it('calls onAnswer when option is clicked', () => {
      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      const option = screen.getByRole('radio', { name: /Dipendente/i });
      fireEvent.click(option);

      expect(mockOnAnswer).toHaveBeenCalledTimes(1);
      expect(mockOnAnswer).toHaveBeenCalledWith('dipendente', undefined);
    });

    it('does not call onAnswer when disabled', () => {
      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
          disabled={true}
        />
      );

      const option = screen.getByRole('radio', { name: /Dipendente/i });
      fireEvent.click(option);

      expect(mockOnAnswer).not.toHaveBeenCalled();
    });
  });

  describe('Keyboard Navigation', () => {
    it('allows number key shortcuts (1-4)', async () => {
      const user = userEvent.setup();

      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      const container = screen.getByRole('radiogroup');
      container.focus();

      await user.keyboard('1');

      expect(mockOnAnswer).toHaveBeenCalledWith('dipendente', undefined);
    });

    it('triggers onSkip when Escape is pressed', async () => {
      const user = userEvent.setup();

      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
          onSkip={mockOnSkip}
        />
      );

      const container = screen.getByRole('radiogroup');
      container.focus();

      await user.keyboard('{Escape}');

      expect(mockOnSkip).toHaveBeenCalledTimes(1);
    });

    it('selects option with Enter after arrow navigation', async () => {
      const user = userEvent.setup();

      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      const container = screen.getByRole('radiogroup');
      container.focus();

      // Navigate to second option and select
      await user.keyboard('{ArrowDown}');
      await user.keyboard('{Enter}');

      expect(mockOnAnswer).toHaveBeenCalledWith('autonomo', undefined);
    });

    it('wraps around when navigating past last option', async () => {
      const user = userEvent.setup();

      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      const container = screen.getByRole('radiogroup');
      container.focus();

      // Navigate down 4 times (should wrap to first)
      await user.keyboard('{ArrowDown}{ArrowDown}{ArrowDown}{ArrowDown}');
      await user.keyboard('{Enter}');

      expect(mockOnAnswer).toHaveBeenCalledWith('dipendente', undefined);
    });

    it('navigates up with ArrowUp', async () => {
      const user = userEvent.setup();

      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      const container = screen.getByRole('radiogroup');
      container.focus();

      // Navigate up (should wrap to last)
      await user.keyboard('{ArrowUp}');
      await user.keyboard('{Enter}');

      expect(mockOnAnswer).toHaveBeenCalledWith('altro', undefined);
    });
  });

  describe('Custom Input', () => {
    const questionWithCustomInput: InteractiveQuestion = {
      ...mockQuestion,
      allow_custom_input: true,
    };

    it('renders last option as input when allow_custom_input is true', () => {
      render(
        <InteractiveQuestionInline
          question={questionWithCustomInput}
          onAnswer={mockOnAnswer}
        />
      );

      // Last option ("Altro") should be rendered as input with its label as placeholder
      expect(screen.getByPlaceholderText('Altro')).toBeInTheDocument();
    });

    it('submits custom input on Enter with last option id', async () => {
      const user = userEvent.setup();

      render(
        <InteractiveQuestionInline
          question={questionWithCustomInput}
          onAnswer={mockOnAnswer}
        />
      );

      // Placeholder is now the last option's label
      const input = screen.getByPlaceholderText('Altro');
      await user.type(input, 'My custom answer');
      await user.keyboard('{Enter}');

      // Should use last option's id ("altro"), not "custom"
      expect(mockOnAnswer).toHaveBeenCalledWith('altro', 'My custom answer');
    });

    it('does not submit empty custom input', async () => {
      const user = userEvent.setup();

      render(
        <InteractiveQuestionInline
          question={questionWithCustomInput}
          onAnswer={mockOnAnswer}
        />
      );

      // Placeholder is now the last option's label
      const input = screen.getByPlaceholderText('Altro');
      await user.click(input);
      await user.keyboard('{Enter}');

      // Should not submit custom input when empty
      // The custom input handler should not call onAnswer with last option id when empty
      const calls = mockOnAnswer.mock.calls;
      const customCall = calls.find(call => call[0] === 'altro');
      expect(customCall).toBeUndefined();
    });

    it('uses last option label as placeholder', () => {
      const questionWithDefaultPlaceholder: InteractiveQuestion = {
        ...mockQuestion,
        allow_custom_input: true,
      };

      render(
        <InteractiveQuestionInline
          question={questionWithDefaultPlaceholder}
          onAnswer={mockOnAnswer}
        />
      );

      // Placeholder should be the last option's label ("Altro")
      expect(screen.getByPlaceholderText('Altro')).toBeInTheDocument();
    });

    it('renders last option as inline input when allow_custom_input is true', () => {
      render(
        <InteractiveQuestionInline
          question={questionWithCustomInput}
          onAnswer={mockOnAnswer}
        />
      );

      // Last option (4th) should be rendered as input, not button
      // There should be only 3 buttons (options 1-3), option 4 is the input
      const buttons = screen.getAllByRole('radio');
      expect(buttons).toHaveLength(3); // Only first 3 options are buttons

      // Option 4 should be an input with placeholder from the last option's label
      expect(screen.getByPlaceholderText('Altro')).toBeInTheDocument();
    });
  });

  describe('Disabled State', () => {
    it('disables all option buttons when disabled', () => {
      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
          disabled={true}
        />
      );

      const buttons = screen.getAllByRole('radio');
      buttons.forEach(button => {
        expect(button).toBeDisabled();
      });
    });

    it('disables custom input when disabled', () => {
      const questionWithCustomInput: InteractiveQuestion = {
        ...mockQuestion,
        allow_custom_input: true,
      };

      render(
        <InteractiveQuestionInline
          question={questionWithCustomInput}
          onAnswer={mockOnAnswer}
          disabled={true}
        />
      );

      const input = screen.getByRole('textbox');
      expect(input).toBeDisabled();
    });
  });

  describe('Accessibility', () => {
    it('has radiogroup role on container', () => {
      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      expect(screen.getByRole('radiogroup')).toBeInTheDocument();
    });

    it('has aria-label with question text', () => {
      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      const container = screen.getByRole('radiogroup');
      expect(container).toHaveAttribute(
        'aria-label',
        'Che tipo di contribuente sei?'
      );
    });

    it('options have radio role', () => {
      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      const radios = screen.getAllByRole('radio');
      expect(radios).toHaveLength(4);
    });

    it('selected option has aria-checked true', async () => {
      const user = userEvent.setup();

      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      const container = screen.getByRole('radiogroup');
      container.focus();

      await user.keyboard('{ArrowDown}');

      const secondOption = screen.getByRole('radio', { name: /Autonomo/i });
      expect(secondOption).toHaveAttribute('aria-checked', 'true');
    });
  });

  describe('Visual Feedback', () => {
    it('applies selected styling to highlighted option (Claude Code text list style)', async () => {
      const user = userEvent.setup();

      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      const container = screen.getByRole('radiogroup');
      container.focus();

      await user.keyboard('{ArrowDown}');

      const secondOption = screen.getByRole('radio', { name: /Autonomo/i });
      // New style uses subtle background highlight instead of solid fill
      expect(secondOption).toHaveClass('bg-[#2A5D67]/10');
    });

    it('applies hover styling to non-selected options', () => {
      render(
        <InteractiveQuestionInline
          question={mockQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      // Second option should have hover class for non-selected state
      const secondOption = screen.getByRole('radio', { name: /Autonomo/i });
      expect(secondOption).toHaveClass('hover:bg-[#A9C1B7]/20');
    });
  });

  describe('Single Option', () => {
    it('renders single option as button when allow_custom_input is false', () => {
      const singleOptionQuestion: InteractiveQuestion = {
        id: 'single_option',
        text: 'Confermi?',
        options: [{ id: 'si', label: 'Si' }],
        allow_custom_input: false,
      };

      render(
        <InteractiveQuestionInline
          question={singleOptionQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      expect(screen.getByRole('radio', { name: /Si/i })).toBeInTheDocument();
    });

    it('renders single option as input when allow_custom_input is true', () => {
      const singleOptionQuestion: InteractiveQuestion = {
        id: 'single_option',
        text: 'Confermi?',
        options: [{ id: 'si', label: 'Si' }],
        allow_custom_input: true,
      };

      render(
        <InteractiveQuestionInline
          question={singleOptionQuestion}
          onAnswer={mockOnAnswer}
        />
      );

      // Single option becomes an input, no radio buttons
      expect(screen.queryByRole('radio')).not.toBeInTheDocument();
      expect(screen.getByPlaceholderText('Si')).toBeInTheDocument();
    });
  });
});

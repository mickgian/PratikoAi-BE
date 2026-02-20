import { render, screen, fireEvent } from '@testing-library/react';
import { IntentSelector } from '../IntentSelector';
import { INTENT_LABELS, INTENT_DISPLAY_NAMES } from '@/types/intentLabeling';

describe('IntentSelector', () => {
  const mockOnSelect = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render all 5 intent buttons', () => {
    render(<IntentSelector selectedIntent={null} onSelect={mockOnSelect} />);

    INTENT_LABELS.forEach(intent => {
      expect(screen.getByTestId(`intent-btn-${intent}`)).toBeInTheDocument();
    });
  });

  it('should display Italian labels', () => {
    render(<IntentSelector selectedIntent={null} onSelect={mockOnSelect} />);

    Object.values(INTENT_DISPLAY_NAMES).forEach(label => {
      expect(screen.getByText(label)).toBeInTheDocument();
    });
  });

  it('should call onSelect when a button is clicked', () => {
    render(<IntentSelector selectedIntent={null} onSelect={mockOnSelect} />);

    fireEvent.click(screen.getByTestId('intent-btn-calculator'));

    expect(mockOnSelect).toHaveBeenCalledWith('calculator');
  });

  it('should highlight the selected intent', () => {
    render(
      <IntentSelector selectedIntent="calculator" onSelect={mockOnSelect} />
    );

    const btn = screen.getByTestId('intent-btn-calculator');
    expect(btn).toHaveClass('text-white');
  });

  it('should respond to keyboard shortcuts 1-5', () => {
    render(<IntentSelector selectedIntent={null} onSelect={mockOnSelect} />);

    fireEvent.keyDown(window, { key: '1' });
    expect(mockOnSelect).toHaveBeenCalledWith('chitchat');

    fireEvent.keyDown(window, { key: '3' });
    expect(mockOnSelect).toHaveBeenCalledWith('technical_research');

    fireEvent.keyDown(window, { key: '5' });
    expect(mockOnSelect).toHaveBeenCalledWith('normative_reference');
  });

  it('should not respond to keyboard when disabled', () => {
    render(
      <IntentSelector selectedIntent={null} onSelect={mockOnSelect} disabled />
    );

    fireEvent.keyDown(window, { key: '1' });
    expect(mockOnSelect).not.toHaveBeenCalled();
  });

  it('should disable buttons when disabled prop is true', () => {
    render(
      <IntentSelector selectedIntent={null} onSelect={mockOnSelect} disabled />
    );

    INTENT_LABELS.forEach(intent => {
      expect(screen.getByTestId(`intent-btn-${intent}`)).toBeDisabled();
    });
  });

  it('should ignore keyboard events from input elements', () => {
    const { container } = render(
      <div>
        <input data-testid="test-input" />
        <IntentSelector selectedIntent={null} onSelect={mockOnSelect} />
      </div>
    );

    const input = container.querySelector('input')!;
    fireEvent.keyDown(input, { key: '1' });

    expect(mockOnSelect).not.toHaveBeenCalled();
  });
});

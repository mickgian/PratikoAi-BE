import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LabelingCard } from '../LabelingCard';
import type { QueueItem } from '@/types/intentLabeling';

const mockItem: QueueItem = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  query: "Come si calcola l'imposta sostitutiva?",
  predicted_intent: 'technical_research',
  confidence: 0.45,
  all_scores: {
    technical_research: 0.45,
    theoretical_definition: 0.3,
    calculator: 0.15,
    chitchat: 0.05,
    golden_set: 0.05,
  },
  expert_intent: null,
  skip_count: 0,
  created_at: '2026-02-03T10:30:00',
};

describe('LabelingCard', () => {
  const mockOnSubmit = jest.fn().mockResolvedValue(undefined);
  const mockOnSkip = jest.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should display the query text', () => {
    render(
      <LabelingCard
        item={mockItem}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
        isSubmitting={false}
      />
    );

    expect(
      screen.getByText(/Come si calcola l'imposta sostitutiva/)
    ).toBeInTheDocument();
  });

  it('should display the predicted intent badge', () => {
    render(
      <LabelingCard
        item={mockItem}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
        isSubmitting={false}
      />
    );

    // Appears in both the predicted intent badge and score distribution
    expect(
      screen.getAllByText('Ricerca Tecnica').length
    ).toBeGreaterThanOrEqual(1);
  });

  it('should display score distribution for all intents', () => {
    render(
      <LabelingCard
        item={mockItem}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
        isSubmitting={false}
      />
    );

    // 45% appears in both confidence bar and score distribution
    expect(screen.getAllByText('45%').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('30%')).toBeInTheDocument();
  });

  it('should submit label after selecting intent and clicking confirm', async () => {
    render(
      <LabelingCard
        item={mockItem}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
        isSubmitting={false}
      />
    );

    // Select an intent
    fireEvent.click(screen.getByTestId('intent-btn-calculator'));

    // Click submit
    fireEvent.click(screen.getByTestId('submit-btn'));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        mockItem.id,
        'calculator',
        undefined
      );
    });
  });

  it('should not submit when no intent is selected', () => {
    render(
      <LabelingCard
        item={mockItem}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
        isSubmitting={false}
      />
    );

    fireEvent.click(screen.getByTestId('submit-btn'));

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('should call onSkip when skip button is clicked', async () => {
    render(
      <LabelingCard
        item={mockItem}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
        isSubmitting={false}
      />
    );

    fireEvent.click(screen.getByTestId('skip-btn'));

    await waitFor(() => {
      expect(mockOnSkip).toHaveBeenCalledWith(mockItem.id);
    });
  });

  it('should toggle notes field with N key', () => {
    render(
      <LabelingCard
        item={mockItem}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
        isSubmitting={false}
      />
    );

    // Notes should not be visible initially
    expect(screen.queryByTestId('labeling-notes')).not.toBeInTheDocument();

    // Press N to toggle notes
    fireEvent.keyDown(window, { key: 'n' });

    expect(screen.getByTestId('labeling-notes')).toBeInTheDocument();

    // Press N again to hide
    fireEvent.keyDown(window, { key: 'n' });

    expect(screen.queryByTestId('labeling-notes')).not.toBeInTheDocument();
  });

  it('should submit with notes when provided', async () => {
    render(
      <LabelingCard
        item={mockItem}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
        isSubmitting={false}
      />
    );

    // Select intent
    fireEvent.click(screen.getByTestId('intent-btn-calculator'));

    // Open notes
    fireEvent.click(screen.getByTestId('notes-toggle'));

    // Type notes
    const textarea = screen.getByTestId('labeling-notes');
    fireEvent.change(textarea, {
      target: { value: 'Richiesta di calcolo' },
    });

    // Submit
    fireEvent.click(screen.getByTestId('submit-btn'));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        mockItem.id,
        'calculator',
        'Richiesta di calcolo'
      );
    });
  });

  it('should clear selection on Escape', () => {
    render(
      <LabelingCard
        item={mockItem}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
        isSubmitting={false}
      />
    );

    // Select an intent
    fireEvent.click(screen.getByTestId('intent-btn-calculator'));

    // Press Escape
    fireEvent.keyDown(window, { key: 'Escape' });

    // Submit should be disabled (no selection)
    const submitBtn = screen.getByTestId('submit-btn');
    expect(submitBtn).toHaveClass('cursor-not-allowed');
  });

  it('should show skip count when item has been skipped', () => {
    const skippedItem = { ...mockItem, skip_count: 3 };

    render(
      <LabelingCard
        item={skippedItem}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
        isSubmitting={false}
      />
    );

    expect(screen.getByText('Saltata 3x')).toBeInTheDocument();
  });

  it('should submit via Enter key shortcut', async () => {
    render(
      <LabelingCard
        item={mockItem}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
        isSubmitting={false}
      />
    );

    // Select intent via keyboard
    fireEvent.keyDown(window, { key: '4' });

    // Submit via Enter
    fireEvent.keyDown(window, { key: 'Enter' });

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        mockItem.id,
        'calculator',
        undefined
      );
    });
  });

  it('should skip via S key shortcut', async () => {
    render(
      <LabelingCard
        item={mockItem}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
        isSubmitting={false}
      />
    );

    fireEvent.keyDown(window, { key: 's' });

    await waitFor(() => {
      expect(mockOnSkip).toHaveBeenCalledWith(mockItem.id);
    });
  });
});

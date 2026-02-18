import { render, screen, fireEvent } from '@testing-library/react';
import { LabelingQueue } from '../LabelingQueue';
import type { QueueItem } from '@/types/intentLabeling';

const mockItems: QueueItem[] = [
  {
    id: 'id-1',
    query: "Come si calcola l'IVA?",
    predicted_intent: 'calculator',
    confidence: 0.35,
    all_scores: { calculator: 0.35, technical_research: 0.3 },
    expert_intent: null,
    skip_count: 0,
    created_at: '2026-02-03T10:30:00',
  },
  {
    id: 'id-2',
    query: 'Ciao, come stai?',
    predicted_intent: 'chitchat',
    confidence: 0.42,
    all_scores: { chitchat: 0.42, theoretical_definition: 0.28 },
    expert_intent: null,
    skip_count: 1,
    created_at: '2026-02-03T11:00:00',
  },
];

describe('LabelingQueue', () => {
  const defaultProps = {
    items: mockItems,
    page: 1,
    totalPages: 3,
    totalCount: 50,
    isLoading: false,
    error: null,
    isSubmitting: false,
    onSubmit: jest.fn(),
    onSkip: jest.fn(),
    onPageChange: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render labeling cards for each item', () => {
    render(<LabelingQueue {...defaultProps} />);

    expect(screen.getAllByTestId('labeling-card')).toHaveLength(2);
  });

  it('should display total count', () => {
    render(<LabelingQueue {...defaultProps} />);

    expect(
      screen.getByText('50 query in attesa di etichettatura')
    ).toBeInTheDocument();
  });

  it('should show loading skeleton when loading', () => {
    render(<LabelingQueue {...defaultProps} isLoading={true} />);

    expect(screen.getByTestId('queue-loading')).toBeInTheDocument();
  });

  it('should show error message on error', () => {
    render(<LabelingQueue {...defaultProps} error="Errore nel caricamento" />);

    expect(screen.getByTestId('queue-error')).toBeInTheDocument();
    expect(screen.getByText('Errore nel caricamento')).toBeInTheDocument();
  });

  it('should show empty state when no items', () => {
    render(<LabelingQueue {...defaultProps} items={[]} />);

    expect(screen.getByTestId('queue-empty')).toBeInTheDocument();
    expect(screen.getByText('Nessuna query in coda')).toBeInTheDocument();
  });

  it('should render pagination when multiple pages', () => {
    render(<LabelingQueue {...defaultProps} />);

    expect(screen.getByText('Precedente')).toBeInTheDocument();
    expect(screen.getByText('Successiva')).toBeInTheDocument();
  });

  it('should call onPageChange when pagination button clicked', () => {
    render(<LabelingQueue {...defaultProps} />);

    fireEvent.click(screen.getByText('Successiva'));

    expect(defaultProps.onPageChange).toHaveBeenCalledWith(2);
  });

  it('should disable previous button on first page', () => {
    render(<LabelingQueue {...defaultProps} page={1} />);

    expect(screen.getByText('Precedente')).toBeDisabled();
  });

  it('should disable next button on last page', () => {
    render(<LabelingQueue {...defaultProps} page={3} totalPages={3} />);

    expect(screen.getByText('Successiva')).toBeDisabled();
  });

  it('should not render pagination when single page', () => {
    render(<LabelingQueue {...defaultProps} totalPages={1} />);

    expect(screen.queryByText('Precedente')).not.toBeInTheDocument();
  });

  it('should show page info', () => {
    render(<LabelingQueue {...defaultProps} page={2} totalPages={5} />);

    expect(screen.getByText('Pagina 2 di 5')).toBeInTheDocument();
  });
});

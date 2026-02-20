import { render, screen } from '@testing-library/react';
import { LabelingDashboard } from '../LabelingDashboard';

// Mock the hooks
jest.mock('@/hooks/useExpertStatus');
jest.mock('../../hooks/useLabelingQueue');
jest.mock('../../hooks/useLabelingStats');
jest.mock('../../hooks/useLabelSubmission');

import { useExpertStatus } from '@/hooks/useExpertStatus';
import { useLabelingQueue } from '../../hooks/useLabelingQueue';
import { useLabelingStats } from '../../hooks/useLabelingStats';
import { useLabelSubmission } from '../../hooks/useLabelSubmission';

const mockUseExpertStatus = useExpertStatus as jest.MockedFunction<
  typeof useExpertStatus
>;
const mockUseLabelingQueue = useLabelingQueue as jest.MockedFunction<
  typeof useLabelingQueue
>;
const mockUseLabelingStats = useLabelingStats as jest.MockedFunction<
  typeof useLabelingStats
>;
const mockUseLabelSubmission = useLabelSubmission as jest.MockedFunction<
  typeof useLabelSubmission
>;

const defaultQueueReturn = {
  items: [],
  page: 1,
  totalCount: 0,
  totalPages: 0,
  isLoading: false,
  error: null,
  removeItem: jest.fn(),
  goToPage: jest.fn(),
  refetch: jest.fn(),
};

const defaultStatsReturn = {
  stats: null,
  isLoading: false,
  error: null,
  refetch: jest.fn(),
};

const defaultSubmissionReturn = {
  isSubmitting: false,
  error: null,
  handleSubmit: jest.fn(),
  handleSkip: jest.fn(),
  clearError: jest.fn(),
};

describe('LabelingDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseLabelingQueue.mockReturnValue(defaultQueueReturn);
    mockUseLabelingStats.mockReturnValue(defaultStatsReturn);
    mockUseLabelSubmission.mockReturnValue(defaultSubmissionReturn);
  });

  it('should show loading state while checking auth', () => {
    mockUseExpertStatus.mockReturnValue({
      isSuperUser: false,
      isExpert: false,
      isLoading: true,
      error: null,
    });

    render(<LabelingDashboard />);

    expect(screen.getByText('Verifica autorizzazione...')).toBeInTheDocument();
  });

  it('should show access denied for non-expert users', () => {
    mockUseExpertStatus.mockReturnValue({
      isSuperUser: false,
      isExpert: false,
      isLoading: false,
      error: null,
    });

    render(<LabelingDashboard />);

    expect(screen.getByTestId('access-denied')).toBeInTheDocument();
    expect(screen.getByText('Accesso non autorizzato')).toBeInTheDocument();
  });

  it('should render dashboard for expert users', () => {
    mockUseExpertStatus.mockReturnValue({
      isSuperUser: true,
      isExpert: true,
      isLoading: false,
      error: null,
    });

    render(<LabelingDashboard />);

    expect(screen.getByTestId('labeling-dashboard')).toBeInTheDocument();
    expect(screen.getByText('Etichettatura Intenti')).toBeInTheDocument();
  });

  it('should render export button for authorized users', () => {
    mockUseExpertStatus.mockReturnValue({
      isSuperUser: true,
      isExpert: true,
      isLoading: false,
      error: null,
    });

    render(<LabelingDashboard />);

    expect(screen.getByTestId('export-btn')).toBeInTheDocument();
  });

  it('should show export badge when new_since_export > 0', () => {
    mockUseExpertStatus.mockReturnValue({
      isSuperUser: true,
      isExpert: true,
      isLoading: false,
      error: null,
    });
    mockUseLabelingStats.mockReturnValue({
      stats: {
        total_queries: 100,
        labeled_queries: 50,
        pending_queries: 50,
        completion_percentage: 50.0,
        labels_by_intent: {},
        new_since_export: 15,
      },
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });

    render(<LabelingDashboard />);

    expect(screen.getByTestId('export-badge')).toBeInTheDocument();
    expect(screen.getByTestId('export-badge')).toHaveTextContent('15');
  });

  it('should not show export badge when new_since_export is 0', () => {
    mockUseExpertStatus.mockReturnValue({
      isSuperUser: true,
      isExpert: true,
      isLoading: false,
      error: null,
    });
    mockUseLabelingStats.mockReturnValue({
      stats: {
        total_queries: 100,
        labeled_queries: 50,
        pending_queries: 50,
        completion_percentage: 50.0,
        labels_by_intent: {},
        new_since_export: 0,
      },
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });

    render(<LabelingDashboard />);

    expect(screen.queryByTestId('export-badge')).not.toBeInTheDocument();
  });

  it('should display Nuove da Esportare stat card', () => {
    mockUseExpertStatus.mockReturnValue({
      isSuperUser: true,
      isExpert: true,
      isLoading: false,
      error: null,
    });
    mockUseLabelingStats.mockReturnValue({
      stats: {
        total_queries: 100,
        labeled_queries: 50,
        pending_queries: 50,
        completion_percentage: 50.0,
        labels_by_intent: {},
        new_since_export: 25,
      },
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });

    render(<LabelingDashboard />);

    expect(screen.getByText('Nuove da Esportare')).toBeInTheDocument();
    // The stat card value and the badge both show 25, so check within the stats bar
    const statsBar = screen.getByTestId('stats-bar');
    expect(statsBar).toHaveTextContent('Nuove da Esportare');
  });

  it('should display submission errors', () => {
    mockUseExpertStatus.mockReturnValue({
      isSuperUser: true,
      isExpert: true,
      isLoading: false,
      error: null,
    });
    mockUseLabelSubmission.mockReturnValue({
      ...defaultSubmissionReturn,
      error: 'Errore nel salvataggio',
    });

    render(<LabelingDashboard />);

    expect(screen.getByText('Errore nel salvataggio')).toBeInTheDocument();
  });

  it('should show empty queue state when no items', () => {
    mockUseExpertStatus.mockReturnValue({
      isSuperUser: true,
      isExpert: true,
      isLoading: false,
      error: null,
    });

    render(<LabelingDashboard />);

    expect(screen.getByTestId('queue-empty')).toBeInTheDocument();
  });
});

/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { UsageDialog } from '../UsageDialog';
import type { UsageStatus } from '@/lib/api/billing';

// Radix Slider requires ResizeObserver which jsdom doesn't provide
beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

const mockUsageData: UsageStatus = {
  plan_slug: 'starter',
  plan_name: 'Starter',
  window_5h: {
    window_type: '5h',
    current_cost_eur: 0.3,
    limit_cost_eur: 1.0,
    usage_percentage: 30,
    reset_at: null,
    reset_in_minutes: 120,
  },
  window_7d: {
    window_type: '7d',
    current_cost_eur: 2.0,
    limit_cost_eur: 5.0,
    usage_percentage: 40,
    reset_at: null,
    reset_in_minutes: 4320,
  },
  credits: { balance_eur: 8.5, extra_usage_enabled: true },
  is_admin: false,
  message_it: 'Tutto nella norma',
};

describe('UsageDialog', () => {
  it('should render usage data with progress bars and plan name', () => {
    const onClose = jest.fn();
    render(<UsageDialog data={mockUsageData} onClose={onClose} />);

    expect(screen.getByTestId('usage-dialog')).toBeInTheDocument();
    expect(screen.getByTestId('usage-card')).toBeInTheDocument();
    expect(screen.getByTestId('plan-name')).toHaveTextContent('Starter');
    expect(screen.getByTestId('credit-balance')).toHaveTextContent('8.50 EUR');
    expect(screen.getAllByTestId('progress-bar-fill')).toHaveLength(2);
  });

  it('should call onClose when Escape key is pressed', () => {
    const onClose = jest.fn();
    render(<UsageDialog data={mockUsageData} onClose={onClose} />);

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('should call onClose when backdrop is clicked', () => {
    const onClose = jest.fn();
    render(<UsageDialog data={mockUsageData} onClose={onClose} />);

    // Click the backdrop (the outer dialog element)
    fireEvent.click(screen.getByTestId('usage-dialog'));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('should NOT call onClose when card content is clicked', () => {
    const onClose = jest.fn();
    render(<UsageDialog data={mockUsageData} onClose={onClose} />);

    // Click on the card content (should be stopped by stopPropagation)
    fireEvent.click(screen.getByTestId('usage-card'));

    expect(onClose).not.toHaveBeenCalled();
  });

  it('should render error message when error prop provided', () => {
    const onClose = jest.fn();
    render(
      <UsageDialog
        data={null}
        error="Errore nel recupero dei dati di utilizzo."
        onClose={onClose}
      />
    );

    expect(screen.getByTestId('usage-dialog')).toBeInTheDocument();
    expect(
      screen.getByText('Errore nel recupero dei dati di utilizzo.')
    ).toBeInTheDocument();
    // Should not render the usage card
    expect(screen.queryByTestId('usage-card')).not.toBeInTheDocument();
  });

  it('should show "Premi Esc per chiudere" footer', () => {
    const onClose = jest.fn();
    render(<UsageDialog data={mockUsageData} onClose={onClose} />);

    expect(screen.getByText('Premi Esc per chiudere')).toBeInTheDocument();
  });

  it('should show "Premi Esc per chiudere" in error state too', () => {
    const onClose = jest.fn();
    render(<UsageDialog data={null} error="Some error" onClose={onClose} />);

    expect(screen.getByText('Premi Esc per chiudere')).toBeInTheDocument();
  });

  it('should NOT show simulator panel for regular users', () => {
    const onClose = jest.fn();
    render(<UsageDialog data={mockUsageData} onClose={onClose} />);

    expect(
      screen.queryByTestId('usage-simulator-panel')
    ).not.toBeInTheDocument();
  });

  it('should show simulator panel when is_admin is true', () => {
    const onClose = jest.fn();
    const adminData = { ...mockUsageData, is_admin: true };
    render(<UsageDialog data={adminData} onClose={onClose} />);

    expect(screen.getByTestId('usage-simulator-panel')).toBeInTheDocument();
  });
});

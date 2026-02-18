/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { UsageSimulatorPanel } from '../UsageSimulatorPanel';

// Radix Slider requires ResizeObserver which jsdom doesn't provide
beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

// Mock billing API
jest.mock('@/lib/api/billing', () => ({
  simulateUsage: jest.fn().mockResolvedValue({
    success: true,
    window_type: '5h',
    target_percentage: 50,
    simulated_cost_eur: 1.25,
    limit_cost_eur: 2.5,
    message_it: 'Simulato',
  }),
  resetUsage: jest.fn().mockResolvedValue({
    success: true,
    windows_cleared: 3,
    redis_keys_cleared: 2,
    message_it: 'Azzerato',
  }),
  getUsageStatus: jest.fn().mockResolvedValue({
    plan_slug: 'base',
    plan_name: 'Base',
    window_5h: {
      window_type: '5h',
      current_cost_eur: 0,
      limit_cost_eur: 2.5,
      usage_percentage: 0,
      reset_at: null,
      reset_in_minutes: null,
    },
    window_7d: {
      window_type: '7d',
      current_cost_eur: 0,
      limit_cost_eur: 7.5,
      usage_percentage: 0,
      reset_at: null,
      reset_in_minutes: null,
    },
    credits: { balance_eur: 0, extra_usage_enabled: false },
    is_admin: true,
    message_it: 'Utilizzo nella norma.',
  }),
}));

describe('UsageSimulatorPanel', () => {
  const onUsageUpdated = jest.fn();

  let sessionRemoveSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();
    sessionRemoveSpy = jest.spyOn(Storage.prototype, 'removeItem');
  });

  afterEach(() => {
    sessionRemoveSpy.mockRestore();
  });

  it('should render sliders with correct labels', () => {
    render(<UsageSimulatorPanel onUsageUpdated={onUsageUpdated} />);

    expect(screen.getByTestId('usage-simulator-panel')).toBeInTheDocument();
    expect(screen.getByText('Sessione 5h')).toBeInTheDocument();
    expect(screen.getByText('Settimana 7g')).toBeInTheDocument();
    expect(screen.getByText('Simulatore utilizzo')).toBeInTheDocument();
  });

  it('should render reset button', () => {
    render(<UsageSimulatorPanel onUsageUpdated={onUsageUpdated} />);

    const resetButton = screen.getByTestId('reset-usage-button');
    expect(resetButton).toBeInTheDocument();
    expect(resetButton).toHaveTextContent('Reset');
  });

  it('should render both slider elements', () => {
    render(<UsageSimulatorPanel onUsageUpdated={onUsageUpdated} />);

    expect(screen.getByTestId('slider-5h')).toBeInTheDocument();
    expect(screen.getByTestId('slider-7d')).toBeInTheDocument();
  });

  it('should call resetUsage and refresh on reset click', async () => {
    const { resetUsage, getUsageStatus } =
      require('@/lib/api/billing') as typeof import('@/lib/api/billing');

    render(<UsageSimulatorPanel onUsageUpdated={onUsageUpdated} />);

    fireEvent.click(screen.getByTestId('reset-usage-button'));

    await waitFor(() => {
      expect(resetUsage).toHaveBeenCalled();
      expect(getUsageStatus).toHaveBeenCalled();
      expect(onUsageUpdated).toHaveBeenCalled();
    });
  });

  it('should clear cost_limit_bypass on reset', async () => {
    sessionStorage.setItem('cost_limit_bypass', 'true');
    localStorage.setItem('pratiko_usage_limit', '{"blocked":true}');

    render(<UsageSimulatorPanel onUsageUpdated={onUsageUpdated} />);

    fireEvent.click(screen.getByTestId('reset-usage-button'));

    await waitFor(() => {
      expect(sessionRemoveSpy).toHaveBeenCalledWith('cost_limit_bypass');
      expect(sessionRemoveSpy).toHaveBeenCalledWith('pratiko_usage_limit');
    });

    expect(sessionStorage.getItem('cost_limit_bypass')).toBeNull();
    expect(localStorage.getItem('pratiko_usage_limit')).toBeNull();
  });

  it('should clear cost_limit_bypass on slider commit', async () => {
    const { simulateUsage } =
      require('@/lib/api/billing') as typeof import('@/lib/api/billing');

    sessionStorage.setItem('cost_limit_bypass', 'true');
    localStorage.setItem('pratiko_usage_limit', '{"blocked":true}');

    render(<UsageSimulatorPanel onUsageUpdated={onUsageUpdated} />);

    // Radix Slider onValueCommit requires pointer capture APIs not available in jsdom.
    // Instead, trigger onValueCommit by programmatically firing a key event on the thumb,
    // which Radix handles via keyboard → commit path.
    const slider5h = screen.getByTestId('slider-5h');
    const thumb = slider5h.querySelector('[role="slider"]');
    expect(thumb).toBeTruthy();

    // Keyboard right arrow triggers onValueChange + onValueCommit in Radix Slider
    fireEvent.keyDown(thumb!, { key: 'ArrowRight' });

    await waitFor(() => {
      expect(simulateUsage).toHaveBeenCalled();
    });

    expect(sessionStorage.getItem('cost_limit_bypass')).toBeNull();
    expect(localStorage.getItem('pratiko_usage_limit')).toBeNull();
  });
});

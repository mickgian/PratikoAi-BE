import { render, screen } from '@testing-library/react';
import { UsageCardMessage } from '../UsageCardMessage';
import type { UsageStatus } from '@/lib/api/billing';

const baseData: UsageStatus = {
  plan_slug: 'starter',
  plan_name: 'Starter',
  window_5h: {
    window_type: '5h',
    current_cost_eur: 0.12,
    limit_cost_eur: 1.0,
    usage_percentage: 12,
    reset_at: '2026-02-13T18:00:00Z',
    reset_in_minutes: 135,
  },
  window_7d: {
    window_type: '7d',
    current_cost_eur: 2.5,
    limit_cost_eur: 10.0,
    usage_percentage: 25,
    reset_at: '2026-02-20T00:00:00Z',
    reset_in_minutes: 4800,
  },
  credits: {
    balance_eur: 5.5,
    extra_usage_enabled: true,
  },
  is_admin: false,
  message_it: 'Utilizzo nella norma.',
};

describe('UsageCardMessage', () => {
  it('renders plan name', () => {
    render(<UsageCardMessage data={baseData} />);
    expect(screen.getByTestId('plan-name')).toHaveTextContent('Starter');
  });

  it('renders percentage progress bars, not EUR costs', () => {
    render(<UsageCardMessage data={baseData} />);

    // Should show percentages
    expect(screen.getByText('12.0%')).toBeInTheDocument();
    expect(screen.getByText('25.0%')).toBeInTheDocument();

    // Should NOT show EUR cost amounts
    expect(screen.queryByText(/0\.12/)).not.toBeInTheDocument();
    expect(screen.queryByText(/1\.00/)).not.toBeInTheDocument();
    expect(screen.queryByText(/2\.50/)).not.toBeInTheDocument();
    expect(screen.queryByText(/10\.00/)).not.toBeInTheDocument();
  });

  it('renders credit balance', () => {
    render(<UsageCardMessage data={baseData} />);
    expect(screen.getByTestId('credit-balance')).toHaveTextContent('5.50 EUR');
  });

  it('renders extra usage badge when enabled', () => {
    render(<UsageCardMessage data={baseData} />);
    expect(screen.getByTestId('extra-usage-badge')).toHaveTextContent(
      'Consumo automatico attivo'
    );
  });

  it('renders extra usage badge when disabled', () => {
    const data = {
      ...baseData,
      credits: { balance_eur: 0, extra_usage_enabled: false },
    };
    render(<UsageCardMessage data={data} />);
    expect(screen.getByTestId('extra-usage-badge')).toHaveTextContent(
      'Consumo automatico disattivato'
    );
  });

  it('renders reset time in Italian format (hours + minutes)', () => {
    render(<UsageCardMessage data={baseData} />);
    // 135 min = 2h 15min
    expect(screen.getByText(/2h 15min/)).toBeInTheDocument();
  });

  it('renders reset time in Italian format (days + hours)', () => {
    render(<UsageCardMessage data={baseData} />);
    // 4800 min = 3g 8h
    expect(screen.getByText(/3g 8h/)).toBeInTheDocument();
  });

  it('renders status message', () => {
    render(<UsageCardMessage data={baseData} />);
    expect(screen.getByTestId('status-message')).toHaveTextContent(
      'Utilizzo nella norma.'
    );
  });

  it('handles 0% usage', () => {
    const data = {
      ...baseData,
      window_5h: { ...baseData.window_5h, usage_percentage: 0 },
    };
    render(<UsageCardMessage data={data} />);
    expect(screen.getByText('0.0%')).toBeInTheDocument();
  });

  it('handles 100%+ usage (progress bar clamped to 100%)', () => {
    const data = {
      ...baseData,
      window_5h: { ...baseData.window_5h, usage_percentage: 120 },
    };
    render(<UsageCardMessage data={data} />);
    expect(screen.getByText('120.0%')).toBeInTheDocument();
    // Bar width should be clamped to 100%
    const fills = screen.getAllByTestId('progress-bar-fill');
    expect(fills[0]).toHaveStyle({ width: '100%' });
  });

  it('handles null reset_in_minutes', () => {
    const data = {
      ...baseData,
      window_5h: { ...baseData.window_5h, reset_in_minutes: null },
    };
    render(<UsageCardMessage data={data} />);
    expect(screen.getByText(/Reset: --/)).toBeInTheDocument();
  });
});

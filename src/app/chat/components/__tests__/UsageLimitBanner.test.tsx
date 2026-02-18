/**
 * @jest-environment jsdom
 */
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UsageLimitBanner } from '../UsageLimitBanner';

describe('UsageLimitBanner', () => {
  const onBypass = jest.fn();
  const onDismiss = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders "Limite di utilizzo raggiunto"', () => {
    render(
      <UsageLimitBanner
        resetAt={new Date(Date.now() + 3600000).toISOString()}
        canBypass={false}
        onBypass={onBypass}
        onDismiss={onDismiss}
      />
    );

    expect(
      screen.getByText('Limite di utilizzo raggiunto')
    ).toBeInTheDocument();
  });

  it('does NOT render cost/euro/percentage text', () => {
    render(
      <UsageLimitBanner
        resetAt={new Date(Date.now() + 3600000).toISOString()}
        canBypass={false}
        onBypass={onBypass}
        onDismiss={onDismiss}
      />
    );

    const banner = screen.getByTestId('usage-limit-banner');
    expect(banner.textContent).not.toMatch(/\d+%/);
    expect(banner.textContent).not.toMatch(/€/);
    expect(banner.textContent).not.toMatch(/euro/i);
  });

  it('shows absolute reset time from resetAt', () => {
    // 2 hours 15 minutes from now
    const resetAt = new Date(Date.now() + (2 * 60 + 15) * 60000).toISOString();

    render(
      <UsageLimitBanner
        resetAt={resetAt}
        canBypass={false}
        onBypass={onBypass}
        onDismiss={onDismiss}
      />
    );

    expect(screen.getByText(/alle \d{2}\.\d{2}/)).toBeInTheDocument();
  });

  it('shows fallback when resetAt is null', () => {
    render(
      <UsageLimitBanner
        resetAt={null}
        canBypass={false}
        onBypass={onBypass}
        onDismiss={onDismiss}
      />
    );

    expect(screen.getByText(/Il limite si azzera a breve/)).toBeInTheDocument();
  });

  it('auto-clears on expiry', () => {
    const resetAt = new Date(Date.now() + 1000).toISOString();

    render(
      <UsageLimitBanner
        resetAt={resetAt}
        canBypass={false}
        onBypass={onBypass}
        onDismiss={onDismiss}
      />
    );

    // Advance past expiry and trigger the interval
    act(() => {
      jest.advanceTimersByTime(31000);
    });

    expect(onDismiss).toHaveBeenCalled();
  });

  it('buttons are NOT red-styled', () => {
    render(
      <UsageLimitBanner
        resetAt={new Date(Date.now() + 3600000).toISOString()}
        canBypass={false}
        onBypass={onBypass}
        onDismiss={onDismiss}
      />
    );

    const upgradeBtn = screen.getByTestId('usage-limit-upgrade');
    const rechargeBtn = screen.getByTestId('usage-limit-recharge');

    // Should use neutral colors, not red
    expect(upgradeBtn.className).toContain('border-[#C4BDB4]');
    expect(upgradeBtn.className).toContain('text-[#2F3E46]');
    expect(upgradeBtn.className).not.toContain('text-red');
    expect(upgradeBtn.className).not.toContain('border-red');

    expect(rechargeBtn.className).toContain('border-[#C4BDB4]');
    expect(rechargeBtn.className).not.toContain('text-red');
  });

  it('does NOT render bypass button when canBypass=false', () => {
    render(
      <UsageLimitBanner
        resetAt={new Date(Date.now() + 3600000).toISOString()}
        canBypass={false}
        onBypass={onBypass}
        onDismiss={onDismiss}
      />
    );

    expect(screen.queryByTestId('usage-limit-bypass')).not.toBeInTheDocument();
  });

  it('renders bypass button when canBypass=true', () => {
    render(
      <UsageLimitBanner
        resetAt={new Date(Date.now() + 3600000).toISOString()}
        canBypass={true}
        onBypass={onBypass}
        onDismiss={onDismiss}
      />
    );

    expect(screen.getByTestId('usage-limit-bypass')).toBeInTheDocument();
  });

  it('does NOT have red background', () => {
    render(
      <UsageLimitBanner
        resetAt={new Date(Date.now() + 3600000).toISOString()}
        canBypass={false}
        onBypass={onBypass}
        onDismiss={onDismiss}
      />
    );

    const banner = screen.getByTestId('usage-limit-banner');
    expect(banner.className).not.toContain('bg-red');
    expect(banner.className).not.toContain('border-red');
  });

  it('does NOT render a dismiss button', () => {
    render(
      <UsageLimitBanner
        resetAt={new Date(Date.now() + 3600000).toISOString()}
        canBypass={false}
        onBypass={onBypass}
        onDismiss={onDismiss}
      />
    );

    expect(screen.queryByTestId('usage-limit-dismiss')).not.toBeInTheDocument();
  });
});

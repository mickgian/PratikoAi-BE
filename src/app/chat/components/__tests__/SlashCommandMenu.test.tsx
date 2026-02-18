/**
 * @jest-environment jsdom
 */
import { render, screen } from '@testing-library/react';
import { SlashCommandMenu, SlashCommandMenuHandle } from '../SlashCommandMenu';
import React from 'react';

describe('SlashCommandMenu', () => {
  const onSelect = jest.fn();
  const onDismiss = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders all commands when filter is "/"', () => {
    render(
      <SlashCommandMenu filter="/" onSelect={onSelect} onDismiss={onDismiss} />
    );
    expect(screen.getByText('/utilizzo')).toBeInTheDocument();
    expect(
      screen.getByText('Mostra lo stato di utilizzo e crediti')
    ).toBeInTheDocument();
  });

  it('filters commands by prefix', () => {
    render(
      <SlashCommandMenu
        filter="/util"
        onSelect={onSelect}
        onDismiss={onDismiss}
      />
    );
    expect(screen.getByText('/utilizzo')).toBeInTheDocument();
  });

  it('shows nothing when no commands match', () => {
    const { container } = render(
      <SlashCommandMenu
        filter="/xyz"
        onSelect={onSelect}
        onDismiss={onDismiss}
      />
    );
    expect(
      container.querySelector('[data-testid="slash-command-menu"]')
    ).toBeNull();
  });

  it('Enter selects the highlighted command', () => {
    const ref = React.createRef<SlashCommandMenuHandle>();
    render(
      <SlashCommandMenu
        ref={ref}
        filter="/"
        onSelect={onSelect}
        onDismiss={onDismiss}
      />
    );
    const handled = ref.current!.handleKey('Enter');
    expect(handled).toBe(true);
    expect(onSelect).toHaveBeenCalledWith('/utilizzo');
  });

  it('Escape calls onDismiss', () => {
    const ref = React.createRef<SlashCommandMenuHandle>();
    render(
      <SlashCommandMenu
        ref={ref}
        filter="/"
        onSelect={onSelect}
        onDismiss={onDismiss}
      />
    );
    ref.current!.handleKey('Escape');
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('ArrowDown wraps activeIndex to first item', () => {
    const ref = React.createRef<SlashCommandMenuHandle>();
    render(
      <SlashCommandMenu
        ref={ref}
        filter="/"
        onSelect={onSelect}
        onDismiss={onDismiss}
      />
    );
    // With only 1 command, ArrowDown should wrap around; Enter selects it
    ref.current!.handleKey('ArrowDown');
    const handled = ref.current!.handleKey('Enter');
    expect(handled).toBe(true);
    expect(onSelect).toHaveBeenCalledWith('/utilizzo');
  });

  it('ArrowUp wraps activeIndex to last item', () => {
    const ref = React.createRef<SlashCommandMenuHandle>();
    render(
      <SlashCommandMenu
        ref={ref}
        filter="/"
        onSelect={onSelect}
        onDismiss={onDismiss}
      />
    );
    ref.current!.handleKey('ArrowUp');
    const handled = ref.current!.handleKey('Enter');
    expect(handled).toBe(true);
    expect(onSelect).toHaveBeenCalledWith('/utilizzo');
  });

  it('returns false from handleKey(Enter) when no matches', () => {
    const ref = React.createRef<SlashCommandMenuHandle>();
    render(
      <SlashCommandMenu
        ref={ref}
        filter="/xyz"
        onSelect={onSelect}
        onDismiss={onDismiss}
      />
    );
    const handled = ref.current!.handleKey('Enter');
    expect(handled).toBe(false);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('getSelected returns the active command name', () => {
    const ref = React.createRef<SlashCommandMenuHandle>();
    render(
      <SlashCommandMenu
        ref={ref}
        filter="/"
        onSelect={onSelect}
        onDismiss={onDismiss}
      />
    );
    expect(ref.current!.getSelected()).toBe('/utilizzo');
  });

  it('getSelected returns null when no matches', () => {
    const ref = React.createRef<SlashCommandMenuHandle>();
    render(
      <SlashCommandMenu
        ref={ref}
        filter="/xyz"
        onSelect={onSelect}
        onDismiss={onDismiss}
      />
    );
    expect(ref.current!.getSelected()).toBeNull();
  });

  it('renders keyboard hint footer when menu is visible', () => {
    render(
      <SlashCommandMenu filter="/" onSelect={onSelect} onDismiss={onDismiss} />
    );
    expect(screen.getByText('Seleziona', { exact: false })).toBeInTheDocument();
    expect(screen.getByText('Completa', { exact: false })).toBeInTheDocument();
    expect(screen.getByText('Chiudi', { exact: false })).toBeInTheDocument();
  });

  it('renders commands in alphabetical order', () => {
    render(
      <SlashCommandMenu filter="/" onSelect={onSelect} onDismiss={onDismiss} />
    );
    const buttons = screen.getAllByRole('button');
    const cmdButtons = buttons.filter(b =>
      b.getAttribute('data-testid')?.startsWith('slash-cmd-')
    );
    expect(cmdButtons.length).toBeGreaterThanOrEqual(1);
    // Verify alphabetical order
    const names = cmdButtons.map(b => b.getAttribute('data-testid'));
    const sorted = [...names].sort();
    expect(names).toEqual(sorted);
  });

  it('does not render keyboard hint when no commands match', () => {
    const { container } = render(
      <SlashCommandMenu
        filter="/xyz"
        onSelect={onSelect}
        onDismiss={onDismiss}
      />
    );
    expect(
      container.querySelector('[data-testid="slash-command-menu"]')
    ).toBeNull();
    expect(screen.queryByText('Seleziona', { exact: false })).toBeNull();
  });
});

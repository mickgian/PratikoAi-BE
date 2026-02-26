/**
 * @file WhatsNewPopup Component Tests
 * @description TDD RED phase - tests for the release notes popup
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { WhatsNewPopup } from '../WhatsNewPopup';

const mockReleaseNote = {
  version: '0.2.0',
  released_at: '2026-02-26T10:00:00Z',
  user_notes:
    'Versione 0.2.0\n\nNovità:\n- Sistema di versioning\n- Note di rilascio',
  technical_notes: 'Added versioning system.',
};

describe('WhatsNewPopup Component', () => {
  describe('Rendering', () => {
    it('should render when a release note is provided', () => {
      render(
        <WhatsNewPopup releaseNote={mockReleaseNote} onDismiss={jest.fn()} />
      );

      expect(screen.getByText(/Novità v0\.2\.0/)).toBeInTheDocument();
    });

    it('should not render when releaseNote is null', () => {
      const { container } = render(
        <WhatsNewPopup releaseNote={null} onDismiss={jest.fn()} />
      );

      expect(container.firstChild).toBeNull();
    });

    it('should display user-facing notes', () => {
      render(
        <WhatsNewPopup releaseNote={mockReleaseNote} onDismiss={jest.fn()} />
      );

      expect(screen.getByText(/Sistema di versioning/)).toBeInTheDocument();
    });

    it('should show dismiss button with Italian text', () => {
      render(
        <WhatsNewPopup releaseNote={mockReleaseNote} onDismiss={jest.fn()} />
      );

      expect(
        screen.getByRole('button', { name: /ho capito/i })
      ).toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    it('should call onDismiss when dismiss button is clicked', () => {
      const onDismiss = jest.fn();
      render(
        <WhatsNewPopup releaseNote={mockReleaseNote} onDismiss={onDismiss} />
      );

      fireEvent.click(screen.getByRole('button', { name: /ho capito/i }));
      expect(onDismiss).toHaveBeenCalledTimes(1);
    });

    it('should call onDismiss with the version', () => {
      const onDismiss = jest.fn();
      render(
        <WhatsNewPopup releaseNote={mockReleaseNote} onDismiss={onDismiss} />
      );

      fireEvent.click(screen.getByRole('button', { name: /ho capito/i }));
      expect(onDismiss).toHaveBeenCalledWith('0.2.0');
    });
  });
});

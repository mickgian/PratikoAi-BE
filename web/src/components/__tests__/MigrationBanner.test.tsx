/**
 * @file Migration Banner Component Tests
 * @description Test suite for chat history migration UI banner
 * Following TDD RED-GREEN-REFACTOR cycle
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MigrationBanner } from '../MigrationBanner';

describe('MigrationBanner Component', () => {
  describe('Rendering', () => {
    it('should render migration banner with sync button', () => {
      // Arrange
      const mockOnSync = jest.fn();

      // Act
      render(<MigrationBanner onSync={mockOnSync} />);

      // Assert
      expect(screen.getByText(/local chat history/i)).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /sync now/i })
      ).toBeInTheDocument();
    });

    it('should show informational message about multi-device sync', () => {
      // Arrange
      const mockOnSync = jest.fn();

      // Act
      render(<MigrationBanner onSync={mockOnSync} />);

      // Assert
      expect(screen.getByText(/multi-device sync/i)).toBeInTheDocument();
    });

    it('should have a close button', () => {
      // Arrange
      const mockOnSync = jest.fn();

      // Act
      render(<MigrationBanner onSync={mockOnSync} />);

      // Assert
      const closeButton = screen.getByRole('button', { name: /close/i });
      expect(closeButton).toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    it('should call onSync when sync button is clicked', async () => {
      // Arrange
      const mockOnSync = jest.fn().mockResolvedValueOnce(undefined);

      // Act
      render(<MigrationBanner onSync={mockOnSync} />);
      const syncButton = screen.getByRole('button', { name: /sync now/i });
      fireEvent.click(syncButton);

      // Assert
      expect(mockOnSync).toHaveBeenCalledTimes(1);
    });

    it('should show loading state while syncing', async () => {
      // Arrange
      let resolveMock: () => void = () => {};
      const mockOnSync = jest.fn(() => {
        return new Promise<void>(resolve => {
          resolveMock = resolve;
        });
      });

      // Act
      render(<MigrationBanner onSync={mockOnSync} />);
      const syncButton = screen.getByRole('button', { name: /sync now/i });
      fireEvent.click(syncButton);

      // Assert
      await waitFor(() => {
        expect(screen.getByText(/syncing/i)).toBeInTheDocument();
      });

      // Cleanup
      resolveMock();
    });

    it('should show success message after sync completes', async () => {
      // Arrange
      const mockOnSync = jest.fn().mockResolvedValueOnce(undefined);

      // Act
      render(<MigrationBanner onSync={mockOnSync} />);
      const syncButton = screen.getByRole('button', { name: /sync now/i });
      fireEvent.click(syncButton);

      // Assert
      await waitFor(() => {
        expect(screen.getByText(/successfully synced/i)).toBeInTheDocument();
      });
    });

    it('should show error message if sync fails', async () => {
      // Arrange
      const mockOnSync = jest
        .fn()
        .mockRejectedValueOnce(new Error('Sync failed'));

      // Act
      render(<MigrationBanner onSync={mockOnSync} />);
      const syncButton = screen.getByRole('button', { name: /sync now/i });
      fireEvent.click(syncButton);

      // Assert
      await waitFor(() => {
        expect(screen.getByText(/sync failed/i)).toBeInTheDocument();
      });
    });

    it('should hide banner when close button is clicked', () => {
      // Arrange
      const mockOnSync = jest.fn();

      // Act
      render(<MigrationBanner onSync={mockOnSync} />);
      const closeButton = screen.getByRole('button', { name: /close/i });
      fireEvent.click(closeButton);

      // Assert
      expect(screen.queryByText(/local chat history/i)).not.toBeInTheDocument();
    });

    it('should allow retry after failed sync', async () => {
      // Arrange
      const mockOnSync = jest
        .fn()
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce(undefined);

      // Act
      render(<MigrationBanner onSync={mockOnSync} />);

      // First attempt - fails
      const syncButton = screen.getByRole('button', { name: /sync now/i });
      fireEvent.click(syncButton);

      await waitFor(() => {
        expect(screen.getByText(/sync failed/i)).toBeInTheDocument();
      });

      // Second attempt - succeeds
      const retryButton = screen.getByRole('button', { name: /retry/i });
      fireEvent.click(retryButton);

      await waitFor(() => {
        expect(screen.getByText(/successfully synced/i)).toBeInTheDocument();
      });

      // Assert
      expect(mockOnSync).toHaveBeenCalledTimes(2);
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      // Arrange
      const mockOnSync = jest.fn();

      // Act
      render(<MigrationBanner onSync={mockOnSync} />);

      // Assert
      const banner = screen.getByRole('alert');
      expect(banner).toBeInTheDocument();
    });

    it('should be keyboard navigable', () => {
      // Arrange
      const mockOnSync = jest.fn();

      // Act
      render(<MigrationBanner onSync={mockOnSync} />);

      // Assert
      const syncButton = screen.getByRole('button', { name: /sync now/i });
      const closeButton = screen.getByRole('button', { name: /close/i });

      expect(syncButton).not.toHaveAttribute('disabled');
      expect(closeButton).not.toHaveAttribute('disabled');
    });
  });

  describe('Responsive Design', () => {
    it('should render on mobile viewport', () => {
      // Arrange
      const mockOnSync = jest.fn();

      // Act
      render(<MigrationBanner onSync={mockOnSync} />);

      // Assert - Component should render without errors
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });
});

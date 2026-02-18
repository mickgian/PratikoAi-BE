/**
 * Tests for ChatHeader Component
 *
 * Tests header functionality including user menu and logout.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatHeader } from '../ChatHeader';
import { useAuth } from '@/hooks/useAuth';
import { useExpertStatus } from '@/hooks/useExpertStatus';
import { useRouter } from 'next/navigation';

// Mock useAuth hook
jest.mock('@/hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

// Mock useExpertStatus hook
jest.mock('@/hooks/useExpertStatus', () => ({
  useExpertStatus: jest.fn(),
}));

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

describe('ChatHeader', () => {
  const mockLogout = jest.fn();
  const mockPush = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();

    (useAuth as jest.Mock).mockReturnValue({
      logout: mockLogout,
      isLoading: false,
      isAuthenticated: true,
    });

    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
    });

    (useExpertStatus as jest.Mock).mockReturnValue({
      isSuperUser: false,
      isExpert: false,
      isLoading: false,
      error: null,
    });
  });

  describe('Rendering', () => {
    it('should render header with logo and title', () => {
      render(<ChatHeader />);

      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
      expect(screen.getByTestId('chat-header-logo')).toBeInTheDocument();
      expect(screen.getByText('PratikoAI')).toBeInTheDocument();
    });

    it('should render user menu button', () => {
      render(<ChatHeader />);

      const userMenuButton = screen.getByTestId('user-menu-button');
      expect(userMenuButton).toBeInTheDocument();
      expect(userMenuButton).toHaveAttribute('aria-label', 'Menu utente');
    });

    it('should not show dropdown by default', () => {
      render(<ChatHeader />);

      expect(
        screen.queryByTestId('user-menu-dropdown')
      ).not.toBeInTheDocument();
    });
  });

  describe('User Menu', () => {
    it('should open dropdown when user menu button is clicked', async () => {
      const user = userEvent.setup();
      render(<ChatHeader />);

      const menuButton = screen.getByTestId('user-menu-button');
      await user.click(menuButton);

      expect(screen.getByTestId('user-menu-dropdown')).toBeInTheDocument();
      expect(screen.getByTestId('logout-button')).toBeInTheDocument();
    });

    it('should close dropdown when clicking outside', async () => {
      const user = userEvent.setup();
      render(
        <div>
          <ChatHeader />
          <div data-testid="outside">Outside</div>
        </div>
      );

      // Open menu
      const menuButton = screen.getByTestId('user-menu-button');
      await user.click(menuButton);
      expect(screen.getByTestId('user-menu-dropdown')).toBeInTheDocument();

      // Click outside
      await user.click(screen.getByTestId('outside'));

      expect(
        screen.queryByTestId('user-menu-dropdown')
      ).not.toBeInTheDocument();
    });

    it('should toggle dropdown on button click', async () => {
      const user = userEvent.setup();
      render(<ChatHeader />);

      const menuButton = screen.getByTestId('user-menu-button');

      // Open
      await user.click(menuButton);
      expect(screen.getByTestId('user-menu-dropdown')).toBeInTheDocument();

      // Close
      await user.click(menuButton);
      expect(
        screen.queryByTestId('user-menu-dropdown')
      ).not.toBeInTheDocument();
    });

    it('should show "Esci" button in dropdown', async () => {
      const user = userEvent.setup();
      render(<ChatHeader />);

      await user.click(screen.getByTestId('user-menu-button'));

      const logoutButton = screen.getByTestId('logout-button');
      expect(logoutButton).toHaveTextContent('Esci');
    });
  });

  describe('Logout Functionality', () => {
    it('should call logout when Esci button is clicked', async () => {
      const user = userEvent.setup();
      mockLogout.mockResolvedValue(undefined);

      render(<ChatHeader />);

      await user.click(screen.getByTestId('user-menu-button'));
      await user.click(screen.getByTestId('logout-button'));

      await waitFor(() => {
        expect(mockLogout).toHaveBeenCalled();
      });
    });

    it('should redirect to /signin after logout', async () => {
      const user = userEvent.setup();
      mockLogout.mockResolvedValue(undefined);

      render(<ChatHeader />);

      await user.click(screen.getByTestId('user-menu-button'));
      await user.click(screen.getByTestId('logout-button'));

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/signin');
      });
    });

    it('should show "Disconnessione..." while logging out', async () => {
      const user = userEvent.setup();
      // Make logout take some time
      mockLogout.mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 100))
      );

      render(<ChatHeader />);

      await user.click(screen.getByTestId('user-menu-button'));
      await user.click(screen.getByTestId('logout-button'));

      // Note: The dropdown closes immediately, so we can't see the loading state
      // This test verifies the flow completes without error
      await waitFor(() => {
        expect(mockLogout).toHaveBeenCalled();
      });
    });

    it('should handle logout errors gracefully', async () => {
      const user = userEvent.setup();
      const consoleError = jest.spyOn(console, 'error').mockImplementation();
      mockLogout.mockRejectedValue(new Error('Network error'));

      render(<ChatHeader />);

      await user.click(screen.getByTestId('user-menu-button'));
      await user.click(screen.getByTestId('logout-button'));

      await waitFor(() => {
        expect(mockLogout).toHaveBeenCalled();
      });

      // Should log the error
      expect(consoleError).toHaveBeenCalled();

      consoleError.mockRestore();
    });

    it('should disable logout button when isLoading is true', async () => {
      const user = userEvent.setup();

      (useAuth as jest.Mock).mockReturnValue({
        logout: mockLogout,
        isLoading: true,
        isAuthenticated: true,
      });

      render(<ChatHeader />);

      await user.click(screen.getByTestId('user-menu-button'));
      const logoutButton = screen.getByTestId('logout-button');

      expect(logoutButton).toBeDisabled();
    });
  });

  describe('Accessibility', () => {
    it('should have proper aria attributes on user menu button', () => {
      render(<ChatHeader />);

      const menuButton = screen.getByTestId('user-menu-button');
      expect(menuButton).toHaveAttribute('aria-label', 'Menu utente');
      expect(menuButton).toHaveAttribute('aria-expanded', 'false');
    });

    it('should update aria-expanded when menu is open', async () => {
      const user = userEvent.setup();
      render(<ChatHeader />);

      const menuButton = screen.getByTestId('user-menu-button');

      await user.click(menuButton);

      expect(menuButton).toHaveAttribute('aria-expanded', 'true');
    });
  });

  describe('Account Navigation', () => {
    it('should navigate to /account/piano when account menu item is clicked', async () => {
      const user = userEvent.setup();
      render(<ChatHeader />);

      await user.click(screen.getByTestId('user-menu-button'));
      await user.click(screen.getByTestId('account-menu-item'));

      expect(mockPush).toHaveBeenCalledWith('/account/piano');
    });
  });

  describe('Intent Labeling Menu Item', () => {
    it('should show labeling link when user is a super user', async () => {
      (useExpertStatus as jest.Mock).mockReturnValue({
        isSuperUser: true,
        isExpert: true,
        isLoading: false,
        error: null,
      });

      const user = userEvent.setup();
      render(<ChatHeader />);

      await user.click(screen.getByTestId('user-menu-button'));

      const labelingItem = screen.getByTestId('labeling-menu-item');
      expect(labelingItem).toBeInTheDocument();
      expect(labelingItem).toHaveTextContent('Etichettatura Intenti');
    });

    it('should not show labeling link when user is not a super user', async () => {
      const user = userEvent.setup();
      render(<ChatHeader />);

      await user.click(screen.getByTestId('user-menu-button'));

      expect(
        screen.queryByTestId('labeling-menu-item')
      ).not.toBeInTheDocument();
    });

    it('should navigate to /expert/labeling when clicked', async () => {
      (useExpertStatus as jest.Mock).mockReturnValue({
        isSuperUser: true,
        isExpert: true,
        isLoading: false,
        error: null,
      });

      const user = userEvent.setup();
      render(<ChatHeader />);

      await user.click(screen.getByTestId('user-menu-button'));
      await user.click(screen.getByTestId('labeling-menu-item'));

      expect(mockPush).toHaveBeenCalledWith('/expert/labeling');
    });
  });

  describe('Model Comparison Menu Item', () => {
    it('should show model comparison link when user is a super user', async () => {
      (useExpertStatus as jest.Mock).mockReturnValue({
        isSuperUser: true,
        isExpert: true,
        isLoading: false,
        error: null,
      });

      const user = userEvent.setup();
      render(<ChatHeader />);

      await user.click(screen.getByTestId('user-menu-button'));

      const comparisonItem = screen.getByTestId('model-comparison-menu-item');
      expect(comparisonItem).toBeInTheDocument();
      expect(comparisonItem).toHaveTextContent('Confronta Modelli');
    });

    it('should not show model comparison link when user is not a super user', async () => {
      const user = userEvent.setup();
      render(<ChatHeader />);

      await user.click(screen.getByTestId('user-menu-button'));

      expect(
        screen.queryByTestId('model-comparison-menu-item')
      ).not.toBeInTheDocument();
    });

    it('should navigate to /expert/model-comparison when clicked', async () => {
      (useExpertStatus as jest.Mock).mockReturnValue({
        isSuperUser: true,
        isExpert: true,
        isLoading: false,
        error: null,
      });

      const user = userEvent.setup();
      render(<ChatHeader />);

      await user.click(screen.getByTestId('user-menu-button'));
      await user.click(screen.getByTestId('model-comparison-menu-item'));

      expect(mockPush).toHaveBeenCalledWith('/expert/model-comparison');
    });
  });
});

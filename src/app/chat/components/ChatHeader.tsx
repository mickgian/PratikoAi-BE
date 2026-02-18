'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Brain,
  Menu,
  User,
  LogOut,
  Tag,
  GitCompare,
  CreditCard,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { useExpertStatus } from '@/hooks/useExpertStatus';

/**
 * Chat header component implementing CHAT_REQUIREMENTS.md specifications
 *
 * Features:
 * - ~72px height with padding and content
 * - White background with subtle bottom border
 * - PratikoAI branding with logo placeholder
 * - Mobile menu button (hidden on desktop)
 * - User menu with logout functionality
 * - Exact Figma color values
 */
export function ChatHeader() {
  const router = useRouter();
  const { logout, isLoading } = useAuth();
  const { isSuperUser } = useExpertStatus();
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        userMenuRef.current &&
        !userMenuRef.current.contains(event.target as Node)
      ) {
        setIsUserMenuOpen(false);
      }
    }

    if (isUserMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () =>
        document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isUserMenuOpen]);

  const handleNavigateToAccount = () => {
    setIsUserMenuOpen(false);
    router.push('/account/piano');
  };

  const handleNavigateToLabeling = () => {
    setIsUserMenuOpen(false);
    router.push('/expert/labeling');
  };

  const handleNavigateToComparison = () => {
    setIsUserMenuOpen(false);
    router.push('/expert/model-comparison');
  };

  // Handle logout
  const handleLogout = async () => {
    if (isLoggingOut) return;

    setIsLoggingOut(true);
    setIsUserMenuOpen(false);

    try {
      await logout();
      // Redirect to signin page after logout
      router.push('/signin');
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <header
      data-testid="chat-header"
      className="bg-white shadow-sm border-b border-[#C4BDB4]/20 p-4 flex items-center justify-between"
    >
      {/* Left side: Mobile menu + Logo + Title */}
      <div
        data-testid="chat-header-content"
        className="flex items-center space-x-3"
      >
        {/* Mobile menu button - hidden on desktop */}
        <button
          data-testid="mobile-menu-button"
          type="button"
          aria-label="Apri menu"
          className="lg:hidden p-2 hover:bg-[#F8F5F1] rounded-lg"
        >
          <Menu className="w-5 h-5 text-[#2A5D67]" />
        </button>

        {/* Logo + Title Group */}
        <div
          data-testid="chat-header-title-group"
          className="flex items-center space-x-3"
        >
          {/* Logo placeholder - 40px x 40px */}
          <div
            data-testid="chat-header-logo"
            className="w-10 h-10 bg-[#2A5D67] rounded-xl flex items-center justify-center"
          >
            <Brain
              data-testid="header-brain-icon"
              className="w-6 h-6 text-white"
            />
          </div>

          {/* Title and status */}
          <div data-testid="chat-header-title">
            <h1 className="text-xl font-semibold text-[#2A5D67]">PratikoAI</h1>
            <p className="text-sm text-[#1E293B]">Online • Pronto</p>
          </div>
        </div>
      </div>

      {/* Right side: User menu */}
      <div className="flex items-center space-x-2">
        <div ref={userMenuRef} className="relative">
          {/* User menu button */}
          <button
            data-testid="user-menu-button"
            type="button"
            onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
            aria-label="Menu utente"
            aria-expanded={isUserMenuOpen}
            className="p-2 hover:bg-[#F8F5F1] rounded-lg transition-colors"
          >
            <User className="w-5 h-5 text-[#2A5D67]" />
          </button>

          {/* Dropdown menu */}
          {isUserMenuOpen && (
            <div
              data-testid="user-menu-dropdown"
              className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-[#C4BDB4]/20 py-1 z-50"
            >
              <button
                data-testid="account-menu-item"
                type="button"
                onClick={handleNavigateToAccount}
                className="w-full px-4 py-2 text-left text-sm text-[#2A5D67] hover:bg-[#F8F5F1] flex items-center space-x-2"
              >
                <CreditCard className="w-4 h-4" />
                <span>Il mio Account</span>
              </button>
              {isSuperUser && (
                <>
                  <button
                    data-testid="labeling-menu-item"
                    type="button"
                    onClick={handleNavigateToLabeling}
                    className="w-full px-4 py-2 text-left text-sm text-[#2A5D67] hover:bg-[#F8F5F1] flex items-center space-x-2"
                  >
                    <Tag className="w-4 h-4" />
                    <span>Etichettatura Intenti</span>
                  </button>
                  <button
                    data-testid="model-comparison-menu-item"
                    type="button"
                    onClick={handleNavigateToComparison}
                    className="w-full px-4 py-2 text-left text-sm text-[#2A5D67] hover:bg-[#F8F5F1] flex items-center space-x-2"
                  >
                    <GitCompare className="w-4 h-4" />
                    <span>Confronta Modelli</span>
                  </button>
                  <div className="border-t border-[#C4BDB4]/20 my-1" />
                </>
              )}
              {/* Logout button */}
              <button
                data-testid="logout-button"
                type="button"
                onClick={handleLogout}
                disabled={isLoggingOut || isLoading}
                className="w-full px-4 py-2 text-left text-sm text-[#2A5D67] hover:bg-[#F8F5F1] flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <LogOut className="w-4 h-4" />
                <span>{isLoggingOut ? 'Disconnessione...' : 'Esci'}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

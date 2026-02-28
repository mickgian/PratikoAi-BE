'use client';

import React, { useState, useCallback } from 'react';
import { ChatHeader } from './ChatHeader';
import { ChatSidebar } from './ChatSidebar';
import { ChatMessagesArea } from './ChatMessagesArea';
import { ChatInputArea } from './ChatInputArea';

/**
 * Main chat layout component implementing CHAT_REQUIREMENTS.md Section 1.2
 *
 * Features:
 * - Full-page chat interface with sidebar + main area
 * - Horizontal flex layout (320px sidebar + flexible main)
 * - Responsive design (sidebar as overlay on mobile, inline on desktop)
 * - Exact Figma color specifications
 * - Integration with useChatState hook
 */
export function ChatLayout() {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  const openMobileSidebar = useCallback(() => {
    setIsMobileSidebarOpen(true);
  }, []);

  const closeMobileSidebar = useCallback(() => {
    setIsMobileSidebarOpen(false);
  }, []);

  return (
    <div data-testid="chat-layout" className="h-screen bg-[#F8F5F1] flex">
      {/* Desktop Sidebar - 320px width, hidden on mobile */}
      <div className="hidden lg:flex w-80 flex-col h-screen">
        <ChatSidebar />
      </div>

      {/* Mobile Sidebar Overlay */}
      {isMobileSidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            data-testid="mobile-sidebar-backdrop"
            className="absolute inset-0 bg-black/50"
            onClick={closeMobileSidebar}
          />
          {/* Sidebar panel */}
          <div className="relative w-80 max-w-[85vw] h-full flex flex-col bg-white shadow-xl">
            <ChatSidebar onClose={closeMobileSidebar} />
          </div>
        </div>
      )}

      {/* Main Chat Area */}
      <main
        data-testid="chat-main-area"
        className="flex-1 flex flex-col h-screen"
        role="main"
      >
        {/* Header - ~72px height */}
        <ChatHeader onMobileMenuToggle={openMobileSidebar} />

        {/* Messages Area - flexible height, scrollable */}
        <ChatMessagesArea />

        {/* Input Area - fixed bottom */}
        <ChatInputArea />
      </main>
    </div>
  );
}

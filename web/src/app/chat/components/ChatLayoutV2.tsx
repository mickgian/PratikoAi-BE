/**
 * @file Chat Layout V2 with Migration Support
 * @description Enhanced ChatLayout with hybrid storage and migration banner
 * Implements Phase 3 of chat history migration
 */

'use client';

import React, { useState, useCallback } from 'react';
import { ChatHeader } from './ChatHeader';
import { ChatSidebar } from './ChatSidebar';
import { ChatMessagesArea } from './ChatMessagesArea';
import { ChatInputArea } from './ChatInputArea';
import { MigrationBanner } from '@/components/MigrationBanner';
import { useSharedChatSessions } from '../hooks/useChatSessions';
import { useChatStorageV2 } from '../hooks/useChatStorageV2';

/**
 * Chat Layout Component with Migration Support
 *
 * **New Features (Phase 3):**
 * - Displays migration banner when IndexedDB data needs sync
 * - Uses hybrid storage (PostgreSQL + IndexedDB fallback)
 * - Handles offline gracefully
 *
 * **Original Features:**
 * - Full-page chat interface with sidebar + main area
 * - Horizontal flex layout (320px sidebar + flexible main)
 * - Responsive design (sidebar as overlay on mobile, inline on desktop)
 * - Exact Figma color specifications
 * - Integration with useChatState hook
 */
export function ChatLayoutV2() {
  const { currentSession } = useSharedChatSessions();
  const sessionId = currentSession?.id || '';

  // Get hybrid storage state for migration detection
  const { migrationNeeded, migrateToBackend, reload } =
    useChatStorageV2(sessionId);

  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  const openMobileSidebar = useCallback(() => {
    setIsMobileSidebarOpen(true);
  }, []);

  const closeMobileSidebar = useCallback(() => {
    setIsMobileSidebarOpen(false);
  }, []);

  // Handle migration completion
  const handleMigrationComplete = async () => {
    // Reload messages from backend after migration
    await reload();
  };

  return (
    <div
      data-testid="chat-layout-v2"
      className="h-screen bg-[#F8F5F1] flex relative"
    >
      {/* Migration Banner (fixed position, above all content) */}
      {migrationNeeded && sessionId && (
        <div className="absolute top-0 left-0 right-0 z-50">
          <MigrationBanner
            onSync={async () => {
              await migrateToBackend();
              await handleMigrationComplete();
            }}
          />
        </div>
      )}

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

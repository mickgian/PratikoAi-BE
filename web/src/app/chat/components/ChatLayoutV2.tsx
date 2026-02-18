/**
 * @file Chat Layout V2 with Migration Support
 * @description Enhanced ChatLayout with hybrid storage and migration banner
 * Implements Phase 3 of chat history migration
 */

'use client';

import React from 'react';
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
 * - Responsive design (sidebar hidden on mobile)
 * - Exact Figma color specifications
 * - Integration with useChatState hook
 */
export function ChatLayoutV2() {
  const { currentSession } = useSharedChatSessions();
  const sessionId = currentSession?.id || '';

  // Get hybrid storage state for migration detection
  const { migrationNeeded, migrateToBackend, reload } =
    useChatStorageV2(sessionId);

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

      {/* Sidebar - 320px width on desktop, collapsible on mobile, same height as main area */}
      <div className="hidden lg:flex w-80 flex-col h-screen">
        <ChatSidebar />
      </div>

      {/* Main Chat Area */}
      <main
        data-testid="chat-main-area"
        className="flex-1 flex flex-col h-screen"
        role="main"
      >
        {/* Header - ~72px height */}
        <ChatHeader />

        {/* Messages Area - flexible height, scrollable */}
        <ChatMessagesArea />

        {/* Input Area - fixed bottom */}
        <ChatInputArea />
      </main>
    </div>
  );
}

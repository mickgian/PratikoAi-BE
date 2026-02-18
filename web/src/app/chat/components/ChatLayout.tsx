'use client';

import React from 'react';
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
 * - Responsive design (sidebar hidden on mobile)
 * - Exact Figma color specifications
 * - Integration with useChatState hook
 */
export function ChatLayout() {
  return (
    <div data-testid="chat-layout" className="h-screen bg-[#F8F5F1] flex">
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

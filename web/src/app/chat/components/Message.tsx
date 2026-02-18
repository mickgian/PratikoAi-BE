'use client';

import React from 'react';
import type { Message as MessageType } from '../types/chat';
import { UserMessage } from './UserMessage';
import { AIMessageV2 } from './AIMessageV2';
import { MessageTimestamp } from './MessageTimestamp';
import { useSharedChatSessions } from '../hooks/useChatSessions';
import clsx from 'clsx';

interface MessageProps {
  message: MessageType;
  isStreaming?: boolean;
  sessionMessages?: MessageType[];
}

/**
 * Message wrapper:
 * - Animate only on first mount (not while streaming)
 * - Memoized to avoid rerenders restarting CSS animations
 */
function MessageInner({
  message,
  isStreaming = false,
  sessionMessages,
}: MessageProps) {
  const { currentSession } = useSharedChatSessions();
  const ariaLabel = `Messaggio da ${message.type}`;

  // DEV-007: Don't render system messages - they should never be displayed to users
  if (message.type === 'system') {
    console.warn(
      '[Message] Attempted to render system message - filtering out',
      { messageId: message.id }
    );
    return null;
  }

  return (
    <article
      data-testid="message-container"
      role="article"
      aria-label={ariaLabel}
      className={clsx(
        'mb-6',
        // ✅ animate only when NOT streaming, so the bubble doesn't "flash"
        !isStreaming && 'animate-fade-slide-up'
      )}
    >
      {message.type === 'user' ? (
        <UserMessage message={message} />
      ) : (
        <AIMessageV2
          message={message}
          isStreaming={isStreaming}
          sessionId={currentSession?.id}
          sessionMessages={sessionMessages}
        />
      )}

      {/* Timestamp – optional to hide while streaming if it moves the layout */}
      <MessageTimestamp
        timestamp={message.timestamp}
        messageType={message.type}
      />
    </article>
  );
}

/** ✅ Prevent useless re-renders of the wrapper */
export const Message = React.memo(
  MessageInner,
  (prev, next) =>
    prev.isStreaming === next.isStreaming &&
    prev.message.id === next.message.id &&
    prev.message.content === next.message.content &&
    prev.message.type === next.message.type &&
    prev.message.timestamp === next.message.timestamp &&
    prev.message.metadata === next.message.metadata &&
    prev.sessionMessages === next.sessionMessages
);

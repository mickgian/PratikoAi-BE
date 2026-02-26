'use client';

import React, { useState } from 'react';
import {
  Brain,
  X,
  Plus,
  MessageSquare,
  Clock,
  Edit2,
  Trash2,
  Check,
  X as XIcon,
  Sparkles,
} from 'lucide-react';
import Link from 'next/link';
import { useUnseenReleaseNote } from '@/lib/hooks/useReleaseNotes';
import { useSharedChatSessions } from '../hooks/useChatSessions';
import { useSharedChatState } from '../hooks/useChatState';
import { LogPrefix } from '../utils/LogPrefix';

/**
 * Chat sidebar component implementing CHAT_REQUIREMENTS.md specifications
 *
 * Features:
 * - 320px width on desktop, full width overlay on mobile
 * - White background with shadow
 * - PratikoAI branding header
 * - New Chat button with session creation
 * - Sessions list with switching capabilities
 * - Active session indicator
 * - Responsive visibility (hidden on mobile, visible on desktop)
 */
export function ChatSidebar() {
  const {
    sessions,
    isLoadingSessions,
    sessionsError,
    currentSession,
    startNewChat,
    switchToSession,
    updateSessionName,
    deleteSession,
    isSessionEmpty,
    hasCompleteQAPair,
    cleanupEmptySessions,
  } = useSharedChatSessions();

  const {
    loadSession,
    clearMessages,
    completeStreaming,
    forceStopStreaming,
    isCurrentlyStreaming,
  } = useSharedChatState();

  // State for editing session names
  const [editingSession, setEditingSession] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  // Handle new chat - clears UI state for new chat
  // Session is created LAZILY when user sends first message (DEV-FE-003)
  // This prevents empty sessions from appearing in the sidebar
  const handleNewChat = () => {
    LogPrefix.log(
      LogPrefix.UI_SIDEBAR,
      'New chat button clicked - clearing UI state (session created lazily on first message)'
    );

    // Clear UI state - session will be created when user sends first message
    startNewChat();

    LogPrefix.log(
      LogPrefix.UI_SIDEBAR,
      'UI cleared for new chat - session will be created on first message send'
    );
  };

  // Handle switching to a different session
  const handleSessionSelect = async (sessionId: string) => {
    LogPrefix.log(LogPrefix.UI_SIDEBAR, 'Session clicked', {
      clickedSessionId: sessionId,
      currentSessionId: currentSession?.id,
      needToSwitch: currentSession?.id !== sessionId,
    });

    try {
      if (currentSession?.id !== sessionId) {
        LogPrefix.log(
          LogPrefix.SESSION_SWITCH,
          `Switching to session: ${sessionId}`
        );

        // Let streaming continue in background - don't interrupt it
        if (isCurrentlyStreaming) {
          LogPrefix.log(
            LogPrefix.STREAM_SESSION,
            'Switching sessions while streaming in background - streaming will continue'
          );
        }

        const messages = await switchToSession(sessionId);
        LogPrefix.log(LogPrefix.SESSION_SWITCH, 'Session switch completed', {
          messagesReceived: messages?.length || 0,
          messagesPreview: messages?.map(m => ({
            type: m.type,
            content: m.content.substring(0, 50),
          })),
        });

        // CRITICAL FIX: Always load messages into chat state, even if empty
        // This ensures chat state is properly synchronized with the session
        LogPrefix.log(
          LogPrefix.SESSION_LOAD,
          'Loading messages into chat state from sidebar',
          {
            sessionId,
            messageCount: messages?.length || 0,
            firstMessagePreview:
              messages?.[0]?.content?.substring(0, 100) || 'none',
          }
        );

        loadSession(sessionId, messages || []);
        LogPrefix.log(
          LogPrefix.SESSION_LOAD,
          'Messages loaded into chat state from sidebar'
        );

        // Additional verification: Check if messages were actually loaded
        setTimeout(() => {
          LogPrefix.log(
            LogPrefix.DEBUG,
            'VERIFICATION: Checking if messages were loaded properly after 100ms'
          );
        }, 100);
      } else {
        LogPrefix.log(
          LogPrefix.SESSION_SWITCH,
          'Session already active, no switch needed'
        );
      }
    } catch (error) {
      LogPrefix.error(LogPrefix.SESSION_SWITCH, 'Failed to switch session', {
        sessionId,
        currentSessionId: currentSession?.id,
        errorMessage: error instanceof Error ? error.message : 'Unknown error',
        error,
      });

      // On error, still try to load empty state to prevent showing old content
      LogPrefix.warn(
        LogPrefix.SESSION_SWITCH,
        'Loading empty state due to session switch error'
      );
      loadSession(sessionId, []);
    }
  };

  // Handle editing session name
  const handleEditSession = (sessionId: string, currentName: string) => {
    setEditingSession(sessionId);
    setEditingName(currentName);
  };

  const handleSaveEdit = async (sessionId: string) => {
    if (editingName.trim() === '') return;

    try {
      await updateSessionName(sessionId, editingName.trim());
      setEditingSession(null);
      setEditingName('');
    } catch (error) {
      console.error('Failed to update session name:', error);
    }
  };

  const handleCancelEdit = () => {
    setEditingSession(null);
    setEditingName('');
  };

  // Handle deleting session
  const handleDeleteSession = async (sessionId: string) => {
    if (!confirm('Sei sicuro di voler eliminare questa conversazione?')) {
      return;
    }

    try {
      await deleteSession(sessionId);
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  // Format session date for display
  const formatSessionDate = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 1) return 'Oggi';
    if (diffDays === 2) return 'Ieri';
    if (diffDays <= 7) return `${diffDays} giorni fa`;

    return date.toLocaleDateString('it-IT', {
      day: 'numeric',
      month: 'short',
    });
  };
  return (
    <aside
      data-testid="chat-sidebar"
      role="complementary"
      className="bg-white shadow-lg flex flex-col h-full"
    >
      <div data-testid="sidebar-content" className="h-full flex flex-col">
        {/* Sidebar Header */}
        <div
          data-testid="sidebar-header"
          className="p-4 border-b border-[#C4BDB4]/20"
        >
          <div className="flex items-center justify-between">
            <div
              data-testid="sidebar-branding"
              className="flex items-center space-x-2"
            >
              {/* Logo - 32px x 32px */}
              <div
                data-testid="sidebar-logo"
                className="w-8 h-8 bg-[#2A5D67] rounded-lg flex items-center justify-center"
              >
                <Brain className="w-5 h-5 text-white" />
              </div>
              <h2 className="font-semibold text-[#2A5D67]">PratikoAI</h2>
            </div>

            {/* Close button - mobile only */}
            <button
              data-testid="sidebar-close-button"
              type="button"
              aria-label="Chiudi sidebar"
              className="p-1 hover:bg-[#F8F5F1] rounded lg:hidden"
            >
              <X className="w-5 h-5 text-[#2A5D67]" />
            </button>
          </div>

          {/* New Chat Button */}
          <button
            data-testid="new-chat-button"
            type="button"
            aria-label="Inizia nuova conversazione"
            onClick={handleNewChat}
            disabled={isLoadingSessions}
            className="w-full mt-3 bg-[#2A5D67] hover:bg-[#1E4B56] disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg flex items-center justify-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>{isLoadingSessions ? 'Creazione...' : 'Nuova Chat'}</span>
          </button>

          {/* Temporary Cleanup Button - Remove after cleaning up empty sessions */}
          {sessions.filter(s => isSessionEmpty(s)).length > 1 && (
            <button
              data-testid="cleanup-button"
              type="button"
              onClick={async () => {
                if (
                  confirm(
                    `Vuoi rimuovere ${sessions.filter(s => isSessionEmpty(s)).length - 1} sessioni vuote duplicate?`
                  )
                ) {
                  await cleanupEmptySessions();
                }
              }}
              aria-label="Pulisci sessioni vuote"
              className="w-full mt-2 bg-orange-600 hover:bg-orange-700 text-white px-3 py-2 rounded-lg flex items-center justify-center space-x-2 text-sm"
            >
              <Trash2 className="w-3 h-3" />
              <span>Pulisci sessioni vuote</span>
            </button>
          )}
        </div>

        {/* Sessions List */}
        <div data-testid="sessions-list" className="flex-1 overflow-y-auto">
          {/* Loading State */}
          {isLoadingSessions && (
            <div
              data-testid="sessions-loading"
              className="flex items-center justify-center py-8 text-[#C4BDB4] text-sm"
            >
              <Clock className="w-4 h-4 mr-2 animate-spin" />
              Caricamento sessioni...
            </div>
          )}

          {/* Error State */}
          {sessionsError && (
            <div
              data-testid="sessions-error"
              className="p-4 text-center text-red-600 text-sm"
            >
              <p>Errore nel caricamento delle sessioni:</p>
              <p className="text-xs mt-1">{sessionsError}</p>
            </div>
          )}

          {/* Sessions List */}
          {!isLoadingSessions && !sessionsError && (
            <div className="p-2">
              {sessions.length === 0 ? (
                <div
                  data-testid="sessions-empty"
                  className="text-center text-[#C4BDB4] text-sm py-8"
                  aria-label="Nessuna sessione presente"
                >
                  <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>Nessuna conversazione</p>
                  <p className="text-xs mt-1">
                    Inizia una nuova chat per cominciare
                  </p>
                </div>
              ) : (
                <div className="space-y-1">
                  {sessions.map(session => (
                    <div
                      key={session.id}
                      data-testid={`session-item-${session.id}`}
                      className={`
                        group rounded-lg transition-colors
                        ${
                          session.isActive
                            ? 'bg-[#2A5D67] text-white'
                            : 'hover:bg-[#F8F5F1] text-[#2A5D67]'
                        }
                      `}
                    >
                      {editingSession === session.id ? (
                        /* Edit Mode */
                        <div className="p-3">
                          <div className="flex items-center space-x-2">
                            <input
                              type="text"
                              value={editingName}
                              onChange={e => setEditingName(e.target.value)}
                              onKeyDown={e => {
                                if (e.key === 'Enter') {
                                  handleSaveEdit(session.id);
                                } else if (e.key === 'Escape') {
                                  handleCancelEdit();
                                }
                              }}
                              className="flex-1 px-2 py-1 text-sm bg-white text-[#2A5D67] border border-[#C4BDB4] rounded focus:outline-none focus:ring-2 focus:ring-[#2A5D67]"
                              autoFocus
                            />
                            <button
                              onClick={() => handleSaveEdit(session.id)}
                              className="p-1 text-green-600 hover:bg-green-600 hover:text-white rounded transition-all duration-200"
                              title="Salva"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button
                              onClick={handleCancelEdit}
                              className="p-1 text-red-600 hover:bg-red-600 hover:text-white rounded transition-all duration-200"
                              title="Annulla"
                            >
                              <XIcon className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ) : (
                        /* Normal Mode */
                        <div className="flex items-stretch">
                          <button
                            onClick={() => handleSessionSelect(session.id)}
                            className="flex-1 text-left p-3 min-w-0"
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1 min-w-0 pr-2">
                                {/* Session Name */}
                                <p
                                  className={`
                                    font-medium text-sm truncate
                                    ${session.isActive ? 'text-white' : 'text-[#2A5D67]'}
                                  `}
                                  title={session.name}
                                >
                                  {session.name}
                                </p>

                                {/* Session Date */}
                                <p
                                  className={`
                                    text-xs mt-1
                                    ${session.isActive ? 'text-white/70' : 'text-[#C4BDB4]'}
                                  `}
                                >
                                  {formatSessionDate(
                                    session.updated_at || session.created_at
                                  )}
                                </p>
                              </div>

                              {/* Active Indicator */}
                              {session.isActive && (
                                <div
                                  data-testid="session-active-indicator"
                                  className="w-2 h-2 bg-white rounded-full flex-shrink-0 mt-1"
                                  aria-label="Sessione attiva"
                                />
                              )}
                            </div>

                            {/* Session Preview - Temporarily disabled to debug 'O' character issue */}
                            {false &&
                              session.message_count &&
                              (session.message_count ?? 0) > 0 && (
                                <p
                                  className={`
                                  text-xs mt-2 truncate
                                  ${session.isActive ? 'text-white/60' : 'text-[#C4BDB4]'}
                                `}
                                >
                                  {session.message_count} messaggi
                                </p>
                              )}
                          </button>

                          {/* Action Buttons - Fixed width area that's always visible */}
                          <div className="flex items-center space-x-1 px-2 py-1 flex-shrink-0 w-16 justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                            {/* Edit Button - Only show for sessions with complete Q&A pairs */}
                            {hasCompleteQAPair(session) && (
                              <button
                                onClick={e => {
                                  e.stopPropagation();
                                  handleEditSession(session.id, session.name);
                                }}
                                className={`
                                  p-1 rounded flex-shrink-0 transition-all duration-200
                                  ${
                                    session.isActive
                                      ? 'text-white hover:bg-white hover:text-[#2A5D67]'
                                      : 'text-[#2A5D67] hover:bg-[#2A5D67] hover:text-white'
                                  }
                                `}
                                title="Modifica nome conversazione"
                              >
                                <Edit2 className="w-3 h-3" />
                              </button>
                            )}

                            {/* Delete Button - TEMPORARILY show for ALL sessions to clean up empty ones */}
                            {/* TODO: Revert to hasCompleteQAPair(session) after cleanup */}
                            {true && (
                              <button
                                onClick={e => {
                                  e.stopPropagation();
                                  handleDeleteSession(session.id);
                                }}
                                className={`
                                  p-1 rounded flex-shrink-0 transition-all duration-200
                                  ${
                                    session.isActive
                                      ? 'text-white hover:bg-white hover:text-red-600'
                                      : 'text-red-600 hover:bg-red-600 hover:text-white'
                                  }
                                `}
                                title="Elimina conversazione"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      {/* Novità link */}
      <div className="p-3 border-t border-gray-100">
        <Link
          href="/novita"
          className="flex items-center space-x-2 px-3 py-2 rounded-lg text-sm text-gray-500 hover:text-[#2A5D67] hover:bg-[#F8F5F1] transition-colors"
        >
          <Sparkles className="w-4 h-4" />
          <span>Novità</span>
        </Link>
      </div>
    </aside>
  );
}

'use client';

import React, { useState, useRef, FormEvent, KeyboardEvent } from 'react';
import { logger } from '@/utils/logger';
import {
  SlashCommandMenu,
  type SlashCommandMenuHandle,
} from './SlashCommandMenu';
import { useInputHistory } from '../hooks/useInputHistory';

interface ChatInputProps {
  onSendMessage: (content: string) => void;
  onSlashCommand?: (cmd: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSendMessage,
  onSlashCommand,
  disabled = false,
  placeholder,
}: ChatInputProps) {
  const [value, setValue] = useState('');
  const lockRef = useRef(false);
  const composingRef = useRef(false);
  const commandMenuRef = useRef<SlashCommandMenuHandle>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const { addToHistory, navigateUp, navigateDown, resetNavigation } =
    useInputHistory();

  const showCommands = value.startsWith('/') && !disabled;

  const safeSend = (raw: string) => {
    const content = raw.trim();
    if (!content) return;

    // idempotency guard (belt & suspenders; ChatInputArea already locks)
    if (lockRef.current) {
      logger.debug('send_blocked_lock', {
        component: 'ChatInput',
        action: 'send_blocked_lock',
      });
      return;
    }
    lockRef.current = true;

    try {
      logger.info('send_submit', {
        component: 'ChatInput',
        action: 'submit',
        metadata: { length: content.length, preview: content.slice(0, 60) },
      });
      // Slash commands bypass the normal message-send pipeline entirely
      if (content.startsWith('/') && onSlashCommand) {
        onSlashCommand(content);
      } else {
        addToHistory(content);
        onSendMessage(content);
      }
      resetNavigation();
      setValue('');
    } finally {
      // release shortly after to ignore quick double actions
      setTimeout(() => {
        lockRef.current = false;
      }, 0);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (disabled) return;
    if (composingRef.current) return;
    safeSend(value);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Input history navigation (only when command menu is closed and input is single-line)
    if (!showCommands && !value.includes('\n')) {
      if (e.key === 'ArrowUp') {
        const prev = navigateUp(value);
        if (prev !== null) {
          e.preventDefault();
          setValue(prev);
        }
        return;
      }
      if (e.key === 'ArrowDown') {
        const next = navigateDown();
        if (next !== null) {
          e.preventDefault();
          setValue(next);
        }
        return;
      }
    }

    // Let command menu handle navigation keys first
    if (showCommands && commandMenuRef.current) {
      if (['ArrowUp', 'ArrowDown'].includes(e.key)) {
        e.preventDefault();
        commandMenuRef.current.handleKey(e.key);
        return;
      }
      if (e.key === 'Tab') {
        e.preventDefault();
        const selected = commandMenuRef.current.getSelected();
        if (selected) {
          setValue(selected);
        }
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setValue('');
        return;
      }
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const handled = commandMenuRef.current.handleKey('Enter');
        if (handled) return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      // prevent newline + prevent the form default submit (we send manually)
      e.preventDefault();
      if (disabled) return;
      if (composingRef.current) return;
      safeSend(value);
    }
  };

  // Build textarea props conditionally to satisfy React 19
  const textareaProps: React.TextareaHTMLAttributes<HTMLTextAreaElement> = {
    value,
    placeholder,
    onChange: e => {
      setValue(e.target.value);
      resetNavigation();
    },
    onKeyDown,
    onCompositionStart: () => (composingRef.current = true),
    onCompositionEnd: () => (composingRef.current = false),
    rows: 1,
    className:
      'flex-1 resize-none rounded-lg border border-[#C4BDB4]/50 bg-white p-3 leading-6 outline-none focus:border-[#9A8F86] focus:ring-2 focus:ring-[#D8D1C8]',
    'aria-disabled': disabled ? 'true' : 'false',
  };

  // Only add readOnly when truly disabled
  if (disabled) {
    textareaProps.readOnly = true;
  }

  // Build button props conditionally
  const buttonDisabled = disabled || !value.trim();

  return (
    <div className="relative" ref={wrapperRef}>
      {showCommands && (
        <SlashCommandMenu
          ref={commandMenuRef}
          filter={value}
          onSelect={cmd => safeSend(cmd)}
          onDismiss={() => setValue('')}
          anchorRef={wrapperRef}
        />
      )}
      <form
        onSubmit={onSubmit}
        className="flex items-end gap-2"
        data-testid="chat-input-form"
        aria-label="Input messaggi"
      >
        <textarea {...textareaProps} />

        <button
          type="submit"
          disabled={buttonDisabled || undefined}
          className="rounded-lg bg-[#2F3E46] px-4 py-2 text-white shadow-sm transition active:scale-[0.98] disabled:opacity-50"
          aria-label="Invia messaggio"
        >
          Invia
        </button>
      </form>
    </div>
  );
}

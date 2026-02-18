'use client';

import React, {
  useState,
  useRef,
  useMemo,
  useImperativeHandle,
  useLayoutEffect,
  forwardRef,
} from 'react';
import { createPortal } from 'react-dom';
import { SLASH_COMMANDS } from '../commands';

export interface SlashCommandMenuHandle {
  handleKey: (key: string) => boolean;
  getSelected: () => string | null;
}

interface SlashCommandMenuProps {
  filter: string;
  onSelect: (cmd: string) => void;
  onDismiss: () => void;
  anchorRef?: React.RefObject<HTMLDivElement | null>;
}

export const SlashCommandMenu = forwardRef<
  SlashCommandMenuHandle,
  SlashCommandMenuProps
>(function SlashCommandMenu({ filter, onSelect, onDismiss, anchorRef }, ref) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [pos, setPos] = useState<{
    bottom: number;
    left: number;
    width: number;
  } | null>(null);

  const matches = useMemo(
    () =>
      SLASH_COMMANDS.filter(c => c.name.startsWith(filter.toLowerCase())).sort(
        (a, b) => a.name.localeCompare(b.name)
      ),
    [filter]
  );

  // Reset selection to first item when filter changes
  const prevFilterRef = useRef(filter);
  if (prevFilterRef.current !== filter) {
    prevFilterRef.current = filter;
    setActiveIndex(0);
  }

  useImperativeHandle(
    ref,
    () => ({
      getSelected(): string | null {
        if (matches.length === 0) return null;
        return matches[activeIndex]?.name ?? null;
      },
      handleKey(key: string): boolean {
        if (key === 'Escape') {
          onDismiss();
          return true;
        }
        if (key === 'ArrowDown') {
          setActiveIndex(i => (matches.length ? (i + 1) % matches.length : 0));
          return true;
        }
        if (key === 'ArrowUp') {
          setActiveIndex(i =>
            matches.length ? (i - 1 + matches.length) % matches.length : 0
          );
          return true;
        }
        if (key === 'Enter') {
          if (matches.length === 0) return false;
          onSelect(matches[activeIndex]?.name ?? matches[0].name);
          return true;
        }
        return false;
      },
    }),
    [matches, activeIndex, onSelect, onDismiss]
  );

  useLayoutEffect(() => {
    if (!anchorRef?.current) return;
    const rect = anchorRef.current.getBoundingClientRect();
    setPos({
      bottom: window.innerHeight - rect.top + 4,
      left: rect.left,
      width: rect.width,
    });
  }, [anchorRef, filter]);

  if (matches.length === 0) return null;

  const menuContent = (
    <div
      data-testid="slash-command-menu"
      className={
        anchorRef
          ? 'fixed z-[100] bg-white rounded-lg shadow-lg border border-[#C4BDB4]/20 overflow-hidden'
          : 'absolute bottom-full mb-1 left-0 right-0 z-50 bg-white rounded-lg shadow-lg border border-[#C4BDB4]/20 overflow-hidden'
      }
      style={
        anchorRef
          ? pos
            ? { bottom: pos.bottom, left: pos.left, width: pos.width }
            : { visibility: 'hidden' as const }
          : undefined
      }
    >
      {matches.map((cmd, i) => (
        <button
          key={cmd.name}
          type="button"
          data-testid={`slash-cmd-${cmd.name}`}
          className={`w-full text-left px-4 py-2.5 flex items-baseline gap-3 transition-colors ${
            i === activeIndex
              ? 'bg-[#E0EDEF] text-[#1A3C42]'
              : 'hover:bg-[#F8F5F1]'
          }`}
          onMouseEnter={() => setActiveIndex(i)}
          onMouseDown={e => {
            e.preventDefault();
            onSelect(cmd.name);
          }}
        >
          <span className="font-mono font-medium text-[#2A5D67] text-sm">
            {cmd.name}
          </span>
          <span className="text-gray-500 text-sm">{cmd.description}</span>
        </button>
      ))}
      <div className="px-4 py-1.5 border-t border-[#C4BDB4]/10 text-xs text-gray-400 flex gap-3">
        <span>
          <kbd className="font-mono">↵</kbd> Seleziona
        </span>
        <span>
          <kbd className="font-mono">Tab</kbd> Completa
        </span>
        <span>
          <kbd className="font-mono">Esc</kbd> Chiudi
        </span>
      </div>
    </div>
  );

  if (anchorRef && typeof document !== 'undefined') {
    return createPortal(menuContent, document.body);
  }
  return menuContent;
});

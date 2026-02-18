'use client';

/**
 * InteractiveQuestionInline Component - DEV-164
 *
 * Renders interactive questions inline in the chat, Claude Code style.
 * Follows the existing PratikoAI design system.
 *
 * Features:
 * - Question text with options grid (single_choice/multi_choice)
 * - Multi-field inputs with Tab navigation (multi_field)
 * - Keyboard navigation (Arrow keys, 1-4 numbers, Enter, Esc)
 * - Custom input field when allow_custom_input
 * - Skip functionality with Esc key
 * - Touch-friendly targets (min 44px)
 * - Responsive grid layout
 * - Fade-slide-up animation on mount
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';

/**
 * Option type for question choices
 */
export interface Option {
  id: string;
  label: string;
  icon?: string;
}

/**
 * Input field for multi-field questions (Claude Code style)
 */
export interface InputField {
  id: string;
  label: string;
  placeholder?: string;
  input_type: 'text' | 'number' | 'currency' | 'date';
  required: boolean;
  validation?: string;
}

/**
 * Interactive question type matching backend schema
 */
export interface InteractiveQuestion {
  id: string;
  text: string;
  question_type?: 'single_choice' | 'multi_choice' | 'multi_field';
  options: Option[];
  fields?: InputField[];
  allow_custom_input?: boolean;
  custom_input_placeholder?: string;
}

interface InteractiveQuestionInlineProps {
  question: InteractiveQuestion;
  onAnswer: (optionId: string, customInput?: string) => void;
  onMultiFieldAnswer?: (fieldValues: Record<string, string>) => void;
  onSkip?: () => void;
  disabled?: boolean;
}

/**
 * InteractiveQuestionInline Component
 *
 * Renders an interactive question with selectable options or multi-field inputs.
 * Supports keyboard navigation and custom input.
 */
export function InteractiveQuestionInline({
  question,
  onAnswer,
  onMultiFieldAnswer,
  onSkip,
  disabled = false,
}: InteractiveQuestionInlineProps) {
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [customText, setCustomText] = useState<string>('');
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const firstFieldRef = useRef<HTMLInputElement>(null);

  const isMultiField = question.question_type === 'multi_field' && question.fields && question.fields.length > 0;

  /**
   * Handle option selection
   */
  const handleSelectOption = useCallback(
    (optionId: string) => {
      if (disabled) return;
      onAnswer(optionId, undefined);
    },
    [disabled, onAnswer]
  );

  /**
   * Handle custom input submission (uses last option's id when allow_custom_input)
   */
  const handleCustomSubmit = useCallback(() => {
    if (disabled || !customText.trim()) return;
    // Use the last option's id for custom input
    const lastOption = question.options[question.options.length - 1];
    onAnswer(lastOption?.id || 'custom', customText.trim());
  }, [disabled, customText, onAnswer, question.options]);

  /**
   * Handle multi-field value change
   */
  const handleFieldChange = useCallback((fieldId: string, value: string) => {
    setFieldValues(prev => ({ ...prev, [fieldId]: value }));
  }, []);

  /**
   * Handle multi-field submission
   */
  const handleMultiFieldSubmit = useCallback(() => {
    if (disabled) return;

    // Check required fields
    const requiredFields = question.fields?.filter(f => f.required) || [];
    const missingRequired = requiredFields.some(f => !fieldValues[f.id]?.trim());
    if (missingRequired) return;

    // Filter out empty values
    const nonEmptyValues: Record<string, string> = {};
    Object.entries(fieldValues).forEach(([key, value]) => {
      if (value.trim()) {
        nonEmptyValues[key] = value.trim();
      }
    });

    onMultiFieldAnswer?.(nonEmptyValues);
  }, [disabled, question.fields, fieldValues, onMultiFieldAnswer]);

  /**
   * Handle keyboard navigation for options
   */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (disabled || isMultiField) return;

      const optionsCount = question.options.length;

      switch (e.key) {
        case 'ArrowDown':
        case 'ArrowRight':
          e.preventDefault();
          setSelectedIndex(prev => (prev + 1) % optionsCount);
          break;

        case 'ArrowUp':
        case 'ArrowLeft':
          e.preventDefault();
          setSelectedIndex(prev => (prev - 1 + optionsCount) % optionsCount);
          break;

        case 'Enter':
          e.preventDefault();
          if (selectedIndex >= 0 && selectedIndex < optionsCount) {
            handleSelectOption(question.options[selectedIndex].id);
          }
          break;

        case 'Escape':
          e.preventDefault();
          onSkip?.();
          break;

        // Number key shortcuts (1-9)
        case '1':
        case '2':
        case '3':
        case '4':
        case '5':
        case '6':
        case '7':
        case '8':
        case '9':
          e.preventDefault();
          const index = parseInt(e.key) - 1;
          if (index < optionsCount) {
            handleSelectOption(question.options[index].id);
          }
          break;
      }
    },
    [disabled, isMultiField, question.options, selectedIndex, handleSelectOption, onSkip]
  );

  /**
   * Handle custom input keydown
   */
  const handleInputKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleCustomSubmit();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onSkip?.();
      }
    },
    [handleCustomSubmit, onSkip]
  );

  /**
   * Handle multi-field input keydown
   */
  const handleMultiFieldKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleMultiFieldSubmit();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onSkip?.();
      }
    },
    [handleMultiFieldSubmit, onSkip]
  );

  // Focus container on mount for keyboard navigation
  useEffect(() => {
    if (isMultiField) {
      // Focus first field for multi-field questions
      firstFieldRef.current?.focus();
    } else {
      containerRef.current?.focus();
    }
  }, [isMultiField]);

  // Render multi-field question (Claude Code style)
  if (isMultiField) {
    return (
      <div
        ref={containerRef}
        className="mt-4 font-mono text-sm animate-fade-slide-up"
        aria-label={question.text}
      >
        {/* Question text with emoji */}
        <p className="text-[#2A5D67] mb-3">❓ {question.text}</p>

        {/* Multi-field inputs */}
        <div className="space-y-2 ml-2">
          {question.fields!.map((field, index) => (
            <div key={field.id} className="flex items-center gap-2">
              <label className="text-[#C4BDB4] w-40 text-right pr-2">
                {field.label}
                {field.required && <span className="text-red-400">*</span>}:
              </label>
              <input
                ref={index === 0 ? firstFieldRef : undefined}
                type={field.input_type === 'currency' || field.input_type === 'number' ? 'number' : field.input_type}
                value={fieldValues[field.id] || ''}
                onChange={e => handleFieldChange(field.id, e.target.value)}
                onKeyDown={handleMultiFieldKeyDown}
                disabled={disabled}
                placeholder={field.placeholder}
                tabIndex={index + 1}
                className={cn(
                  'flex-1 bg-transparent border-b border-[#C4BDB4]/50',
                  'text-sm text-[#2A5D67] placeholder:text-[#C4BDB4]',
                  'focus:outline-none focus:border-[#2A5D67]',
                  'transition-colors duration-150',
                  'disabled:opacity-50 disabled:cursor-not-allowed',
                  'max-w-[200px]'
                )}
                aria-label={field.label}
                aria-required={field.required}
              />
              {field.input_type === 'currency' && (
                <span className="text-[#C4BDB4]">€</span>
              )}
            </div>
          ))}
        </div>

        {/* Submit button */}
        <div className="mt-4 ml-2 flex items-center gap-4">
          <button
            type="button"
            onClick={handleMultiFieldSubmit}
            disabled={disabled}
            className={cn(
              'px-4 py-1 rounded',
              'bg-[#2A5D67] text-white',
              'hover:bg-[#2A5D67]/90',
              'focus:outline-none focus:ring-2 focus:ring-[#2A5D67]/50',
              'transition-colors duration-150',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            Continua
          </button>
          <p className="text-xs text-[#C4BDB4]">
            (Tab per spostarti, Enter per confermare, Esc per saltare)
          </p>
        </div>
      </div>
    );
  }

  // Render single/multi choice question (original behavior)
  return (
    <div
      ref={containerRef}
      className="mt-4 font-mono text-sm animate-fade-slide-up"
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="radiogroup"
      aria-label={question.text}
    >
      {/* Question text with emoji */}
      <p className="text-[#2A5D67] mb-2">❓ {question.text}</p>

      {/* Options as numbered text list - Claude Code style */}
      <div className="space-y-1 ml-2">
        {question.options.map((option, index) => {
          const isLastOption = index === question.options.length - 1;
          const renderAsInput = question.allow_custom_input && isLastOption;

          // When allow_custom_input, render last option as inline input
          if (renderAsInput) {
            return (
              <div
                key={option.id}
                className={cn(
                  'flex items-center py-1 px-2 rounded transition-colors duration-150',
                  'min-h-[32px]',
                  'hover:bg-[#A9C1B7]/20'
                )}
              >
                <span className="text-[#C4BDB4] mr-2">{index + 1}.</span>
                <input
                  ref={inputRef}
                  type="text"
                  value={customText}
                  onChange={e => setCustomText(e.target.value)}
                  onKeyDown={handleInputKeyDown}
                  disabled={disabled}
                  placeholder={option.label}
                  className={cn(
                    'flex-1 bg-transparent border-b border-[#C4BDB4]/50',
                    'text-sm text-[#2A5D67] placeholder:text-[#C4BDB4]',
                    'focus:outline-none focus:border-[#2A5D67]',
                    'transition-colors duration-150',
                    'disabled:opacity-50 disabled:cursor-not-allowed'
                  )}
                  aria-label={option.label}
                />
              </div>
            );
          }

          // Regular option as button
          return (
            <button
              key={option.id}
              type="button"
              onClick={() => handleSelectOption(option.id)}
              disabled={disabled}
              role="radio"
              aria-checked={selectedIndex === index}
              className={cn(
                'block w-full text-left py-1 px-2 rounded transition-colors duration-150',
                'min-h-[32px]', // Touch-friendly but compact
                selectedIndex === index
                  ? 'bg-[#2A5D67]/10'
                  : 'hover:bg-[#A9C1B7]/20',
                'focus-visible:outline-none focus-visible:bg-[#2A5D67]/10',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              <span className="text-[#C4BDB4] mr-2">{index + 1}.</span>
              <span className="text-[#2A5D67]">{option.label}</span>
            </button>
          );
        })}
      </div>

      {/* Skip hint */}
      <p className="text-xs text-[#C4BDB4] mt-2 ml-2">
        (Premi 1-{Math.min(question.options.length, 9)} o Esc per saltare)
      </p>
    </div>
  );
}

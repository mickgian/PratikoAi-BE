'use client';

import { motion } from 'motion/react';
import { Check } from 'lucide-react';
import type { Step } from '../types';

interface ProcedureStepperProps {
  steps: Step[];
  currentStepIndex: number;
  onStepClick: (index: number) => void;
}

export function ProcedureStepper({
  steps,
  currentStepIndex,
  onStepClick,
}: ProcedureStepperProps) {
  return (
    <div className="mb-8">
      <div className="flex items-start justify-between relative">
        <div
          className="absolute top-5 left-0 right-0 h-0.5 bg-[#C4BDB4]/30"
          style={{ zIndex: 0 }}
        />

        {steps.map((step, index) => (
          <div
            key={step.id}
            className="flex flex-col items-center relative"
            style={{ flex: 1, zIndex: 1 }}
          >
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => onStepClick(index)}
              className={`w-10 h-10 rounded-full flex items-center justify-center transition-all mb-2 ${
                step.completed
                  ? 'bg-green-500 text-white'
                  : index === currentStepIndex
                    ? 'bg-[#2A5D67] text-white ring-4 ring-[#2A5D67]/20'
                    : 'bg-white text-[#1E293B] border-2 border-[#C4BDB4]'
              }`}
            >
              {step.completed ? (
                <Check className="w-5 h-5" />
              ) : (
                <span className="font-semibold text-sm">{step.number}</span>
              )}
            </motion.button>
            <span
              className={`text-xs text-center max-w-[100px] ${
                index === currentStepIndex
                  ? 'font-semibold text-[#2A5D67]'
                  : 'text-[#1E293B]'
              }`}
            >
              {step.title.length > 20
                ? step.title.substring(0, 20) + '...'
                : step.title}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

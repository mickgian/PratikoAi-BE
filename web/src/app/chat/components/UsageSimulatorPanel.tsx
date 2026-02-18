'use client';

import { useState, useCallback } from 'react';
import * as Slider from '@radix-ui/react-slider';
import { RotateCcw } from 'lucide-react';
import { simulateUsage, resetUsage, getUsageStatus } from '@/lib/api/billing';
import type { UsageStatus } from '@/lib/api/billing';

interface UsageSimulatorPanelProps {
  onUsageUpdated: (data: UsageStatus) => void;
}

interface SliderState {
  value: number;
  loading: boolean;
}

function WindowSlider({
  label,
  windowType,
  state,
  onChange,
  onCommit,
}: {
  label: string;
  windowType: string;
  state: SliderState;
  onChange: (value: number) => void;
  onCommit: (windowType: string, value: number) => void;
}) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-amber-800">
        <span>{label}</span>
        <span className={state.loading ? 'animate-pulse' : ''}>
          {state.value}%
        </span>
      </div>
      <Slider.Root
        className="relative flex items-center select-none touch-none w-full h-5"
        value={[state.value]}
        min={0}
        max={110}
        step={5}
        disabled={state.loading}
        onValueChange={([v]) => onChange(v)}
        onValueCommit={([v]) => onCommit(windowType, v)}
        data-testid={`slider-${windowType}`}
      >
        <Slider.Track className="bg-amber-200 relative grow rounded-full h-1.5">
          <Slider.Range className="absolute bg-amber-500 rounded-full h-full" />
        </Slider.Track>
        <Slider.Thumb className="block w-4 h-4 bg-amber-600 rounded-full shadow focus:outline-none focus:ring-2 focus:ring-amber-400" />
      </Slider.Root>
    </div>
  );
}

export function UsageSimulatorPanel({
  onUsageUpdated,
}: UsageSimulatorPanelProps) {
  const [slider5h, setSlider5h] = useState<SliderState>({
    value: 0,
    loading: false,
  });
  const [slider7d, setSlider7d] = useState<SliderState>({
    value: 0,
    loading: false,
  });
  const [resetting, setResetting] = useState(false);

  const handleCommit = useCallback(
    async (windowType: string, value: number) => {
      const setSt = windowType === '5h' ? setSlider5h : setSlider7d;
      setSt(prev => ({ ...prev, loading: true }));
      sessionStorage.removeItem('cost_limit_bypass');
      localStorage.removeItem('pratiko_usage_limit');
      try {
        await simulateUsage(windowType, value);
        const updated = await getUsageStatus();
        onUsageUpdated(updated);
      } catch {
        // Revert on error
      } finally {
        setSt(prev => ({ ...prev, loading: false }));
      }
    },
    [onUsageUpdated]
  );

  const handleReset = useCallback(async () => {
    setResetting(true);
    sessionStorage.removeItem('cost_limit_bypass');
    localStorage.removeItem('pratiko_usage_limit');
    try {
      await resetUsage();
      setSlider5h({ value: 0, loading: false });
      setSlider7d({ value: 0, loading: false });
      const updated = await getUsageStatus();
      onUsageUpdated(updated);
    } catch {
      // Ignore
    } finally {
      setResetting(false);
    }
  }, [onUsageUpdated]);

  return (
    <div
      className="bg-amber-50 border border-amber-300 rounded-xl p-4 space-y-3"
      data-testid="usage-simulator-panel"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-amber-900">
          Simulatore utilizzo
        </span>
        <button
          onClick={handleReset}
          disabled={resetting}
          className="flex items-center gap-1 text-xs text-amber-700 hover:text-amber-900 disabled:opacity-50"
          data-testid="reset-usage-button"
        >
          <RotateCcw
            className={`w-3.5 h-3.5 ${resetting ? 'animate-spin' : ''}`}
          />
          Reset
        </button>
      </div>

      <WindowSlider
        label="Sessione 5h"
        windowType="5h"
        state={slider5h}
        onChange={v => setSlider5h(prev => ({ ...prev, value: v }))}
        onCommit={handleCommit}
      />

      <WindowSlider
        label="Settimana 7g"
        windowType="7d"
        state={slider7d}
        onChange={v => setSlider7d(prev => ({ ...prev, value: v }))}
        onCommit={handleCommit}
      />
    </div>
  );
}

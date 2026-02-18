# Agent Monitoring Dashboard - Complete Specification

**Version:** 1.0
**Created:** 2025-11-27
**Purpose:** Real-time monitoring dashboard for multi-agent development workflow
**Status:** Specification Phase

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Design System Specifications](#design-system-specifications)
3. [Dashboard Requirements](#dashboard-requirements)
4. [Architecture & Data Flow](#architecture--data-flow)
5. [Component Specifications](#component-specifications)
6. [Backend Implementation](#backend-implementation)
7. [Frontend Implementation](#frontend-implementation)
8. [Mobile-Responsive Patterns](#mobile-responsive-patterns)
9. [Implementation Phases](#implementation-phases)
10. [Technical Stack](#technical-stack)

---

## Executive Summary

### Purpose
Real-time dashboard to monitor all 9 PratikoAI development agents:
- @Mario (Business Analyst)
- @Egidio (Architect)
- @Ezio (Backend Expert)
- @Livia (Frontend Expert)
- @Primo (Database Designer)
- @Clelia (Test Validation)
- @Valerio (Performance Optimizer)
- @Tiziano (Debug Specialist)
- @Severino (Security Auditor)

### Key Principles
- **Concise Overview**: High-level status, NOT detailed logs
- **Mobile-Friendly**: Responsive design matching PratikoAi-BE/web
- **Real-Time**: WebSocket streaming for live updates
- **Design Consistency**: Exact color palette, icons, and components from PratikoAi-BE/web

### Data Philosophy
- **UI Shows**: Agent status, current task, progress, errors, key metrics
- **Daily Logs Capture**: Detailed transcript lines, tool calls, raw JSONL data
- **Retention**: UI = real-time only, Logs = 30 days

---

## Design System Specifications

### Color Palette (from PratikoAi-BE/web)

```typescript
// Primary Colors
const colors = {
  // Main Brand
  'blu-petrolio': '#2A5D67',      // Primary brand color, headers, active states
  'avorio': '#F8F5F1',            // Background, subtle accents

  // Accent Colors
  'verde-salvia': '#A9C1B7',      // Success states, positive metrics
  'oro-antico': '#D4A574',        // Warnings, important highlights
  'grigio-tortora': '#C4BDB4',    // Muted text, secondary info

  // Functional Colors
  'white': '#FFFFFF',             // Card backgrounds
  'green-600': '#16A34A',         // Success indicators
  'red-600': '#DC2626',           // Error indicators
  'yellow-600': '#CA8A04',        // Warning indicators
  'blue-600': '#2563EB',          // Info indicators
};
```

### Typography

```typescript
// Font: Inter
// Location: /Users/micky/WebstormProjects/PratikoAi-BE/web/src/app/layout.tsx

import { Inter } from "next/font/google";

const inter = Inter({
  subsets: ["latin"],
  weight: ['400', '500', '600', '700', '900'],
  variable: '--font-inter',
});

// Usage
font-normal   // 400
font-medium   // 500
font-semibold // 600
font-bold     // 700
font-black    // 900
```

### Icons (Lucide React)

```typescript
// Source: /Users/micky/WebstormProjects/PratikoAi-BE/web/src/app/(protected)/dashboard/page.tsx

import {
  Activity,      // Agent activity, live status
  Brain,         // AI/agent intelligence
  Clock,         // Time tracking, duration
  Users,         // Multiple agents
  TrendingUp,    // Progress, metrics
  AlertCircle,   // Warnings, errors
  CheckCircle2,  // Success, completion
  XCircle,       // Failures, errors
  Pause,         // Paused agents
  Play,          // Active agents
  FileText,      // Task documentation
  Code,          // Code-related tasks
  Database,      // Database operations
  Shield,        // Security operations
  Zap,           // Performance
  Bug,           // Debugging
} from 'lucide-react';
```

### Component Library

```typescript
// Source: PratikoAi-BE/web uses Radix UI + shadcn/ui pattern
// Location: /Users/micky/WebstormProjects/PratikoAi-BE/web/src/components/ui/

// Core Components
- Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter
- Badge
- Tabs, TabsList, TabsTrigger, TabsContent
- Progress
- Avatar, AvatarImage, AvatarFallback
- ScrollArea
```

### Responsive Breakpoints

```typescript
// Source: tailwind.config.ts
screens: {
  'sm': '640px',   // Mobile landscape
  'md': '768px',   // Tablet
  'lg': '1024px',  // Desktop (primary breakpoint)
  'xl': '1280px',  // Large desktop
  '2xl': '1536px', // Extra large
}

// Mobile-first approach: Use lg: prefix for desktop-specific styles
```

---

## Dashboard Requirements

### Functional Requirements

#### FR-1: Agent Status Monitoring
- **Display**: Real-time status of all 9 agents
- **States**: `idle`, `active`, `paused`, `error`, `completed`
- **Visual**: Color-coded badges + icons
- **Update Frequency**: < 2 seconds latency

#### FR-2: Current Task Visibility
- **Display**: Currently executing task for each active agent
- **Info**: Task ID, title, phase (RED/GREEN/BLUE), progress %
- **Actions**: Click to see task details (modal/drawer)

#### FR-3: Task History
- **Display**: Last 10 completed tasks per agent
- **Info**: Task ID, duration, status (success/failure), timestamp
- **Filter**: By agent, by date range, by status

#### FR-4: Error Alerts
- **Display**: Real-time error notifications
- **Info**: Agent name, task ID, error type, timestamp
- **Action**: Click to see full error details + suggested fixes

#### FR-5: Performance Metrics
- **Display**: Aggregate metrics (cards at top)
  - Total tasks completed today
  - Average task duration
  - Success rate (%)
  - Active agents count
- **Charts**: Optional line chart showing tasks/hour (simplified)

#### FR-6: Mobile Support
- **Requirement**: Fully functional on mobile devices (>375px width)
- **Pattern**: Card-based layout, vertical scrolling, touch-friendly

### Non-Functional Requirements

#### NFR-1: Performance
- **Page Load**: < 2 seconds initial load
- **WebSocket Latency**: < 2 seconds for status updates
- **UI Responsiveness**: 60 FPS animations/transitions

#### NFR-2: Data Retention
- **UI State**: Real-time only (cleared on page refresh)
- **Daily Logs**: 30 days retention in `/logs/agents/YYYY-MM-DD.jsonl`
- **Database**: 90 days retention for metrics/task history

#### NFR-3: Scalability
- **Concurrent Agents**: Support up to 9 agents running simultaneously
- **WebSocket Connections**: Handle 10+ concurrent dashboard viewers
- **Database**: Optimize for 1000+ tasks/day

---

## Architecture & Data Flow

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Browser                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Agent Dashboard (React + TypeScript + Tailwind)      │  │
│  │  - AgentGrid: Shows all 9 agents                      │  │
│  │  - TaskList: Current + recent tasks                   │  │
│  │  - MetricsCards: Aggregate stats                      │  │
│  └───────────────────────────────────────────────────────┘  │
│           ▲                                    ▲             │
│           │ HTTP (initial)                     │ WebSocket   │
│           │                                    │ (real-time) │
└───────────┼────────────────────────────────────┼─────────────┘
            │                                    │
┌───────────┼────────────────────────────────────┼─────────────┐
│           ▼                                    ▼             │
│  ┌─────────────────┐                ┌──────────────────┐    │
│  │  FastAPI REST   │                │  WebSocket       │    │
│  │  Endpoints      │                │  Handler         │    │
│  │                 │                │                  │    │
│  │ GET /agents     │                │ /ws/dashboard    │    │
│  │ GET /tasks      │                │                  │    │
│  │ GET /metrics    │                │ Broadcasts:      │    │
│  └─────────────────┘                │ - agent_status   │    │
│           │                         │ - task_update    │    │
│           │                         │ - error_alert    │    │
│           │                         └──────────────────┘    │
│           │                                    ▲             │
│           │                                    │             │
│           ▼                                    │             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │          PostgreSQL Database                         │   │
│  │                                                       │   │
│  │  Tables:                                              │   │
│  │  - agent_sessions                                     │   │
│  │  - agent_tasks                                        │   │
│  │  - agent_metrics                                      │   │
│  │  - agent_errors                                       │   │
│  └──────────────────────────────────────────────────────┘   │
│           ▲                                                  │
│           │                                                  │
└───────────┼──────────────────────────────────────────────────┘
            │
┌───────────┼──────────────────────────────────────────────────┐
│           │                                                  │
│  ┌────────▼────────────────────────────────────────────┐    │
│  │  SubagentStop Hooks (.claude/hooks/*)               │    │
│  │                                                       │    │
│  │  On agent completion:                                │    │
│  │  1. Parse transcript JSONL                           │    │
│  │  2. Extract task info (ID, status, duration)         │    │
│  │  3. POST to /api/v1/agents/tasks                     │    │
│  │  4. WebSocket broadcast to dashboard                 │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  Claude Code Agent Execution                                 │
└───────────────────────────────────────────────────────────────┘
```

### Data Flow

#### Flow 1: Initial Page Load
```
1. User navigates to /dashboard/agents
2. Frontend makes parallel HTTP requests:
   GET /api/v1/agents/status        → Current status of all 9 agents
   GET /api/v1/agents/tasks/recent  → Last 10 tasks per agent
   GET /api/v1/agents/metrics/today → Aggregate metrics
3. Frontend renders initial state
4. Frontend establishes WebSocket connection to /ws/dashboard
```

#### Flow 2: Agent Starts Task
```
1. User/Claude invokes agent: Task subagent_type="ezio" prompt="..."
2. Claude Code spawns agent subprocess
3. (Future) SubagentStart hook fires → POST /api/v1/agents/status
4. Database: INSERT INTO agent_sessions (agent_id, status='active', task_id)
5. WebSocket broadcast: { type: 'agent_status', agent: 'ezio', status: 'active' }
6. Frontend updates: AgentCard shows green "Active" badge
```

#### Flow 3: Agent Completes Task
```
1. Agent finishes execution
2. SubagentStop hook fires (.claude/hooks/subagent_stop/log_agent_task.sh)
3. Hook script:
   - Parses ~/.claude_code/logs/transcripts/<session_id>.jsonl
   - Extracts: task_id, agent_name, duration, status, error_count
   - POST /api/v1/agents/tasks with JSON payload
4. Backend:
   - INSERT INTO agent_tasks (task_id, agent_id, duration, status, ...)
   - UPDATE agent_sessions SET status='idle'
   - WebSocket broadcast: { type: 'task_completed', agent: 'ezio', task: {...} }
5. Frontend:
   - Updates AgentCard: status → idle
   - Adds task to TaskList
   - Updates metrics cards
```

#### Flow 4: Error Occurs
```
1. Agent encounters error during execution
2. SubagentStop hook detects error in transcript (status='error')
3. Hook extracts error details:
   - Error message
   - Stack trace
   - Failed tool call
4. POST /api/v1/agents/errors
5. Database: INSERT INTO agent_errors (agent_id, task_id, error_type, message, ...)
6. WebSocket broadcast: { type: 'error_alert', agent: 'ezio', error: {...} }
7. Frontend:
   - Shows red notification badge
   - Updates AgentCard with red "Error" status
   - (Optional) Toast notification
```

### Database Schema

```sql
-- Table: agent_sessions
-- Purpose: Track current state of each agent
CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(50) NOT NULL,  -- 'mario', 'ezio', 'livia', etc.
    agent_name VARCHAR(100) NOT NULL,  -- 'Business Analyst', 'Backend Expert', etc.
    status VARCHAR(20) NOT NULL,  -- 'idle', 'active', 'paused', 'error'
    current_task_id VARCHAR(100),  -- Reference to task currently executing
    started_at TIMESTAMP,
    last_heartbeat TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_agent_sessions_agent_id ON agent_sessions(agent_id);
CREATE INDEX idx_agent_sessions_status ON agent_sessions(status);

-- Table: agent_tasks
-- Purpose: Historical record of all tasks executed by agents
CREATE TABLE agent_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(100) NOT NULL,  -- 'DEV-BE-93', etc.
    agent_id VARCHAR(50) NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    task_title TEXT,
    task_description TEXT,
    status VARCHAR(20) NOT NULL,  -- 'success', 'failure', 'cancelled'
    phase VARCHAR(10),  -- 'RED', 'GREEN', 'BLUE'
    duration_seconds INTEGER,
    error_count INTEGER DEFAULT 0,
    test_count INTEGER DEFAULT 0,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_agent_tasks_agent_id ON agent_tasks(agent_id);
CREATE INDEX idx_agent_tasks_status ON agent_tasks(status);
CREATE INDEX idx_agent_tasks_started_at ON agent_tasks(started_at DESC);

-- Table: agent_errors
-- Purpose: Detailed error tracking for debugging
CREATE TABLE agent_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(50) NOT NULL,
    task_id VARCHAR(100),
    error_type VARCHAR(50),  -- 'tool_error', 'timeout', 'syntax_error', etc.
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    context JSONB,  -- Additional context (file path, line number, etc.)
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_agent_errors_agent_id ON agent_errors(agent_id);
CREATE INDEX idx_agent_errors_created_at ON agent_errors(created_at DESC);
CREATE INDEX idx_agent_errors_resolved ON agent_errors(resolved);

-- Table: agent_metrics
-- Purpose: Pre-aggregated metrics for fast dashboard queries
CREATE TABLE agent_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    agent_id VARCHAR(50) NOT NULL,
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    avg_duration_seconds INTEGER,
    total_errors INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_agent_metrics_date_agent ON agent_metrics(date, agent_id);
CREATE INDEX idx_agent_metrics_date ON agent_metrics(date DESC);
```

---

## Component Specifications

### 1. AgentGrid Component

**Purpose**: Display all 9 agents with real-time status

**Location**: `/Users/micky/WebstormProjects/PratikoAi-BE/web/src/app/(protected)/dashboard/agents/page.tsx`

**Code Example**:

```tsx
'use client';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Activity, Brain, Clock, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useAgentStatus } from '@/hooks/useAgentStatus';

const AGENTS = [
  { id: 'mario', name: 'Mario', role: 'Business Analyst', icon: Brain, color: '#2A5D67' },
  { id: 'egidio', name: 'Egidio', role: 'Architect', icon: Brain, color: '#2A5D67' },
  { id: 'ezio', name: 'Ezio', role: 'Backend Expert', icon: Code, color: '#2A5D67' },
  { id: 'livia', name: 'Livia', role: 'Frontend Expert', icon: Code, color: '#2A5D67' },
  { id: 'primo', name: 'Primo', role: 'Database Designer', icon: Database, color: '#2A5D67' },
  { id: 'clelia', name: 'Clelia', role: 'Test Validation', icon: CheckCircle2, color: '#A9C1B7' },
  { id: 'valerio', name: 'Valerio', role: 'Performance', icon: Zap, color: '#D4A574' },
  { id: 'tiziano', name: 'Tiziano', role: 'Debug Specialist', icon: Bug, color: '#DC2626' },
  { id: 'severino', name: 'Severino', role: 'Security Auditor', icon: Shield, color: '#16A34A' },
];

const STATUS_CONFIG = {
  idle: { label: 'Idle', color: 'bg-gray-200 text-gray-800', icon: Pause },
  active: { label: 'Active', color: 'bg-green-100 text-green-800', icon: Activity },
  error: { label: 'Error', color: 'bg-red-100 text-red-800', icon: AlertCircle },
  completed: { label: 'Completed', color: 'bg-blue-100 text-blue-800', icon: CheckCircle2 },
};

export default function AgentGrid() {
  const { agents, loading } = useAgentStatus(); // WebSocket hook

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-6">
      {AGENTS.map((agent) => {
        const agentData = agents[agent.id];
        const status = agentData?.status || 'idle';
        const StatusIcon = STATUS_CONFIG[status].icon;
        const AgentIcon = agent.icon;

        return (
          <Card key={agent.id} className="bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-[#C4BDB4]">
                {agent.name}
              </CardTitle>
              <AgentIcon className="h-4 w-4 text-[#C4BDB4]" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-2xl font-bold text-[#2A5D67]">
                    {agentData?.currentTask || '—'}
                  </div>
                  <p className="text-xs text-[#C4BDB4] mt-1">
                    {agent.role}
                  </p>
                </div>
                <Badge className={STATUS_CONFIG[status].color}>
                  <StatusIcon className="h-3 w-3 mr-1" />
                  {STATUS_CONFIG[status].label}
                </Badge>
              </div>

              {agentData?.duration && (
                <div className="flex items-center mt-3 text-xs text-[#C4BDB4]">
                  <Clock className="h-3 w-3 mr-1" />
                  {formatDuration(agentData.duration)}
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}m ${secs}s`;
}
```

### 2. TaskList Component

**Purpose**: Show recent tasks with status and duration

**Code Example**:

```tsx
'use client';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { FileText, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { useRecentTasks } from '@/hooks/useRecentTasks';

export default function TaskList() {
  const { tasks, loading } = useRecentTasks(10); // Last 10 tasks

  return (
    <Card className="bg-white rounded-xl shadow-sm">
      <CardHeader>
        <CardTitle className="text-lg font-semibold text-[#2A5D67]">
          Recent Tasks
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {tasks.map((task) => (
            <div
              key={task.id}
              className="flex items-start justify-between p-3 rounded-lg bg-[#F8F5F1] hover:bg-[#C4BDB4]/20 transition-colors"
            >
              <div className="flex items-start space-x-3 flex-1">
                <FileText className="h-5 w-5 text-[#2A5D67] mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-[#2A5D67]">
                      {task.task_id}
                    </span>
                    <Badge variant="outline" className="text-xs">
                      {task.agent_name}
                    </Badge>
                  </div>
                  <p className="text-xs text-[#C4BDB4] mt-1 line-clamp-2">
                    {task.task_title}
                  </p>
                  <div className="flex items-center space-x-3 mt-2 text-xs text-[#C4BDB4]">
                    <span className="flex items-center">
                      <Clock className="h-3 w-3 mr-1" />
                      {formatDuration(task.duration_seconds)}
                    </span>
                    <span>{formatRelativeTime(task.completed_at)}</span>
                  </div>
                </div>
              </div>
              <div className="ml-3">
                {task.status === 'success' ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-600" />
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}
```

### 3. MetricsCards Component

**Purpose**: Aggregate statistics at top of dashboard

**Code Example**:

```tsx
'use client';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Activity, CheckCircle2, Clock, TrendingUp } from 'lucide-react';
import { useMetrics } from '@/hooks/useMetrics';

export default function MetricsCards() {
  const { metrics, loading } = useMetrics();

  const cards = [
    {
      title: 'Active Agents',
      value: metrics?.activeAgents || 0,
      change: metrics?.activeAgentsDelta || 0,
      icon: Activity,
      color: 'text-[#2A5D67]',
    },
    {
      title: 'Tasks Today',
      value: metrics?.tasksToday || 0,
      change: metrics?.tasksTodayDelta || 0,
      icon: CheckCircle2,
      color: 'text-[#A9C1B7]',
    },
    {
      title: 'Avg Duration',
      value: metrics?.avgDuration ? `${metrics.avgDuration}s` : '—',
      change: metrics?.avgDurationDelta || 0,
      icon: Clock,
      color: 'text-[#D4A574]',
    },
    {
      title: 'Success Rate',
      value: metrics?.successRate ? `${metrics.successRate}%` : '—',
      change: metrics?.successRateDelta || 0,
      icon: TrendingUp,
      color: 'text-[#16A34A]',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 p-6">
      {cards.map((card) => (
        <Card key={card.title} className="bg-white rounded-xl shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-[#C4BDB4]">
              {card.title}
            </CardTitle>
            <card.icon className={`h-4 w-4 ${card.color}`} />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-[#2A5D67]">
              {card.value}
            </div>
            {card.change !== 0 && (
              <p className="text-xs text-[#C4BDB4] mt-1">
                <span className={card.change > 0 ? 'text-green-600' : 'text-red-600'}>
                  {card.change > 0 ? '+' : ''}{card.change}
                </span>{' '}
                from hour ago
              </p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

### 4. WebSocket Hook (useAgentStatus)

**Purpose**: Real-time updates via WebSocket

**Code Example**:

```tsx
// hooks/useAgentStatus.ts
import { useState, useEffect } from 'react';

interface AgentStatus {
  status: 'idle' | 'active' | 'error' | 'completed';
  currentTask?: string;
  duration?: number;
}

export function useAgentStatus() {
  const [agents, setAgents] = useState<Record<string, AgentStatus>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Initial HTTP fetch
    fetch('/api/v1/agents/status')
      .then((res) => res.json())
      .then((data) => {
        setAgents(data.agents);
        setLoading(false);
      });

    // WebSocket connection
    const ws = new WebSocket('ws://localhost:8000/ws/dashboard');

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === 'agent_status') {
        setAgents((prev) => ({
          ...prev,
          [message.agent]: {
            status: message.status,
            currentTask: message.currentTask,
            duration: message.duration,
          },
        }));
      }

      if (message.type === 'task_completed') {
        setAgents((prev) => ({
          ...prev,
          [message.agent]: {
            ...prev[message.agent],
            status: 'idle',
            currentTask: undefined,
            duration: undefined,
          },
        }));
      }
    };

    return () => ws.close();
  }, []);

  return { agents, loading };
}
```

---

## Backend Implementation

### FastAPI Endpoints

```python
# app/api/v1/agents.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.websockets import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
import json

from app.models.database import get_db
from app.models.agent_monitoring import AgentSession, AgentTask, AgentError, AgentMetrics
from app.services.websocket_manager import manager

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

# ============================================================================
# REST Endpoints
# ============================================================================

@router.get("/status")
async def get_agent_status(db: Session = Depends(get_db)):
    """Get current status of all agents"""
    sessions = db.query(AgentSession).all()

    agents = {}
    for session in sessions:
        agents[session.agent_id] = {
            "status": session.status,
            "currentTask": session.current_task_id,
            "startedAt": session.started_at.isoformat() if session.started_at else None,
            "duration": (datetime.now() - session.started_at).seconds if session.started_at else None,
        }

    return {"agents": agents}


@router.get("/tasks/recent")
async def get_recent_tasks(limit: int = 10, db: Session = Depends(get_db)):
    """Get recent tasks across all agents"""
    tasks = (
        db.query(AgentTask)
        .order_by(AgentTask.completed_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "tasks": [
            {
                "id": str(task.id),
                "task_id": task.task_id,
                "agent_id": task.agent_id,
                "agent_name": task.agent_name,
                "task_title": task.task_title,
                "status": task.status,
                "duration_seconds": task.duration_seconds,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            }
            for task in tasks
        ]
    }


@router.get("/metrics/today")
async def get_today_metrics(db: Session = Depends(get_db)):
    """Get aggregate metrics for today"""
    today = date.today()

    metrics = db.query(AgentMetrics).filter(AgentMetrics.date == today).all()

    total_completed = sum(m.tasks_completed for m in metrics)
    total_failed = sum(m.tasks_failed for m in metrics)
    avg_duration = sum(m.avg_duration_seconds for m in metrics) // len(metrics) if metrics else 0
    success_rate = (total_completed / (total_completed + total_failed) * 100) if (total_completed + total_failed) > 0 else 0

    active_agents = db.query(AgentSession).filter(AgentSession.status == 'active').count()

    return {
        "activeAgents": active_agents,
        "tasksToday": total_completed,
        "avgDuration": avg_duration,
        "successRate": round(success_rate, 1),
        "activeAgentsDelta": 0,  # TODO: Calculate from previous hour
        "tasksTodayDelta": 0,    # TODO: Calculate from yesterday
        "avgDurationDelta": 0,   # TODO: Calculate from yesterday
        "successRateDelta": 0,   # TODO: Calculate from yesterday
    }


@router.post("/tasks")
async def create_task(
    task_id: str,
    agent_id: str,
    agent_name: str,
    task_title: str,
    status: str,
    duration_seconds: int,
    started_at: str,
    completed_at: str,
    error_count: int = 0,
    db: Session = Depends(get_db),
):
    """Create task record (called by SubagentStop hook)"""
    task = AgentTask(
        task_id=task_id,
        agent_id=agent_id,
        agent_name=agent_name,
        task_title=task_title,
        status=status,
        duration_seconds=duration_seconds,
        error_count=error_count,
        started_at=datetime.fromisoformat(started_at),
        completed_at=datetime.fromisoformat(completed_at),
    )
    db.add(task)

    # Update agent session
    session = db.query(AgentSession).filter(AgentSession.agent_id == agent_id).first()
    if session:
        session.status = 'idle'
        session.current_task_id = None

    db.commit()

    # Broadcast to WebSocket clients
    await manager.broadcast(json.dumps({
        "type": "task_completed",
        "agent": agent_id,
        "task": {
            "task_id": task_id,
            "status": status,
            "duration_seconds": duration_seconds,
        },
    }))

    return {"success": True}


@router.post("/errors")
async def create_error(
    agent_id: str,
    task_id: str,
    error_type: str,
    error_message: str,
    stack_trace: str = None,
    db: Session = Depends(get_db),
):
    """Create error record (called by SubagentStop hook)"""
    error = AgentError(
        agent_id=agent_id,
        task_id=task_id,
        error_type=error_type,
        error_message=error_message,
        stack_trace=stack_trace,
    )
    db.add(error)
    db.commit()

    # Broadcast to WebSocket clients
    await manager.broadcast(json.dumps({
        "type": "error_alert",
        "agent": agent_id,
        "error": {
            "type": error_type,
            "message": error_message,
        },
    }))

    return {"success": True}


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@router.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket connection for real-time dashboard updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive (client sends ping every 30s)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

### WebSocket Manager

```python
# app/services/websocket_manager.py

from fastapi import WebSocket
from typing import List
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                # Connection closed, remove it
                self.disconnect(connection)

manager = ConnectionManager()
```

### SubagentStop Hook Script

```bash
#!/bin/bash
# .claude/hooks/subagent_stop/log_agent_task.sh

# Extract transcript file path (passed by Claude Code)
TRANSCRIPT_FILE="$1"
AGENT_TYPE="$2"

# Parse transcript JSONL to extract task info
TASK_DATA=$(python3 << EOF
import json
import sys
from datetime import datetime

transcript_file = "$TRANSCRIPT_FILE"
agent_type = "$AGENT_TYPE"

# Read last 100 lines of transcript (most recent activity)
with open(transcript_file, 'r') as f:
    lines = f.readlines()[-100:]

# Extract task info
task_id = None
task_title = None
started_at = None
completed_at = None
error_count = 0
status = 'success'

for line in lines:
    try:
        entry = json.loads(line)

        # Extract task ID from prompt
        if 'content' in entry and 'DEV-BE-' in entry['content']:
            import re
            match = re.search(r'(DEV-BE-\d+)', entry['content'])
            if match:
                task_id = match.group(1)

        # Extract timestamps
        if 'timestamp' in entry:
            ts = entry['timestamp']
            if not started_at:
                started_at = ts
            completed_at = ts

        # Count errors
        if entry.get('type') == 'error':
            error_count += 1
            status = 'failure'
    except:
        continue

# Calculate duration
if started_at and completed_at:
    start = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
    end = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
    duration = int((end - start).total_seconds())
else:
    duration = 0

# Output JSON
print(json.dumps({
    'task_id': task_id or 'unknown',
    'agent_id': agent_type,
    'agent_name': agent_type.capitalize(),
    'task_title': task_title or 'Untitled Task',
    'status': status,
    'duration_seconds': duration,
    'error_count': error_count,
    'started_at': started_at or datetime.now().isoformat(),
    'completed_at': completed_at or datetime.now().isoformat(),
}))
EOF
)

# POST to backend API
curl -X POST http://localhost:8000/api/v1/agents/tasks \
  -H "Content-Type: application/json" \
  -d "$TASK_DATA"

# Write to daily log file
LOG_DIR="/Users/micky/PycharmProjects/PratikoAi-BE/logs/agents"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date +%Y-%m-%d).jsonl"

echo "$TASK_DATA" >> "$LOG_FILE"
```

---

## Frontend Implementation

### Page Structure

```
/Users/micky/WebstormProjects/PratikoAi-BE/web/
└── src/
    └── app/
        └── (protected)/
            └── dashboard/
                └── agents/
                    ├── page.tsx           # Main dashboard page
                    ├── components/
                    │   ├── AgentGrid.tsx
                    │   ├── TaskList.tsx
                    │   ├── MetricsCards.tsx
                    │   └── ErrorAlerts.tsx
                    └── hooks/
                        ├── useAgentStatus.ts
                        ├── useRecentTasks.ts
                        └── useMetrics.ts
```

### Main Dashboard Page

```tsx
// src/app/(protected)/dashboard/agents/page.tsx

import { Suspense } from 'react';
import MetricsCards from './components/MetricsCards';
import AgentGrid from './components/AgentGrid';
import TaskList from './components/TaskList';
import ErrorAlerts from './components/ErrorAlerts';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function AgentDashboardPage() {
  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      {/* Header */}
      <div className="bg-white border-b border-[#C4BDB4]/20">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <h1 className="text-2xl font-bold text-[#2A5D67]">
            Agent Monitoring Dashboard
          </h1>
          <p className="text-sm text-[#C4BDB4] mt-1">
            Real-time overview of multi-agent development workflow
          </p>
        </div>
      </div>

      {/* Metrics Cards */}
      <Suspense fallback={<MetricsCardsSkeleton />}>
        <MetricsCards />
      </Suspense>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        <Tabs defaultValue="agents" className="space-y-4">
          <TabsList className="bg-white border border-[#C4BDB4]/20">
            <TabsTrigger value="agents">Agents</TabsTrigger>
            <TabsTrigger value="tasks">Tasks</TabsTrigger>
            <TabsTrigger value="errors">Errors</TabsTrigger>
          </TabsList>

          <TabsContent value="agents" className="space-y-4">
            <Suspense fallback={<AgentGridSkeleton />}>
              <AgentGrid />
            </Suspense>
          </TabsContent>

          <TabsContent value="tasks" className="space-y-4">
            <Suspense fallback={<TaskListSkeleton />}>
              <TaskList />
            </Suspense>
          </TabsContent>

          <TabsContent value="errors" className="space-y-4">
            <Suspense fallback={<ErrorAlertsSkeleton />}>
              <ErrorAlerts />
            </Suspense>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
```

---

## Mobile-Responsive Patterns

### Breakpoint Strategy

```tsx
// Desktop-first approach with mobile overrides

// ❌ BAD (mobile last)
<div className="grid grid-cols-3 gap-4">

// ✅ GOOD (mobile first)
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
```

### Card Stacking

```tsx
// Desktop: 3-column grid
// Tablet: 2-column grid
// Mobile: 1-column stack

<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
  {agents.map(...)}
</div>
```

### Text Truncation

```tsx
// Prevent text overflow on small screens

<p className="text-sm text-[#C4BDB4] line-clamp-2">
  {task.task_description}
</p>

// line-clamp-2 = max 2 lines with ellipsis
```

### Touch-Friendly Targets

```tsx
// Minimum 44px × 44px tap targets on mobile

<button className="p-3 min-h-[44px] min-w-[44px]">
  <Icon className="h-5 w-5" />
</button>
```

### Responsive Typography

```tsx
// Scale text down on mobile

<h1 className="text-xl md:text-2xl lg:text-3xl font-bold">
  Agent Dashboard
</h1>
```

---

## Implementation Phases

### Phase 1: Database & Backend API (1 week)
**Owner**: @Primo (database schema) + @Ezio (backend API)

**Tasks**:
- [ ] Create database schema (agent_sessions, agent_tasks, agent_errors, agent_metrics)
- [ ] Write Alembic migration
- [ ] Implement FastAPI endpoints:
  - [ ] GET /api/v1/agents/status
  - [ ] GET /api/v1/agents/tasks/recent
  - [ ] GET /api/v1/agents/metrics/today
  - [ ] POST /api/v1/agents/tasks
  - [ ] POST /api/v1/agents/errors
  - [ ] WS /ws/dashboard
- [ ] Create WebSocket manager service
- [ ] Write unit tests (7+ tests per endpoint)
- [ ] Integration tests (E2E flows)

**Acceptance Criteria**:
- [ ] All endpoints return expected status codes
- [ ] WebSocket broadcasts messages correctly
- [ ] Database migrations run without errors
- [ ] Test coverage ≥49%

---

### Phase 2: SubagentStop Hook (3 days)
**Owner**: @Ezio (bash scripting + Python parsing)

**Tasks**:
- [ ] Create `.claude/hooks/subagent_stop/log_agent_task.sh`
- [ ] Implement transcript JSONL parsing (Python)
- [ ] Extract task metadata (ID, duration, status, errors)
- [ ] POST to backend API
- [ ] Write to daily log file (`logs/agents/YYYY-MM-DD.jsonl`)
- [ ] Test hook with sample transcripts
- [ ] Document hook configuration

**Acceptance Criteria**:
- [ ] Hook fires reliably on agent completion
- [ ] Correctly extracts task ID from transcript
- [ ] Handles errors gracefully (doesn't crash)
- [ ] Daily log files created correctly

---

### Phase 3: Frontend Components (1 week)
**Owner**: @Livia (frontend expert)

**Tasks**:
- [ ] Create page: `/dashboard/agents/page.tsx`
- [ ] Implement components:
  - [ ] MetricsCards (aggregate stats)
  - [ ] AgentGrid (9 agent cards)
  - [ ] TaskList (recent tasks)
  - [ ] ErrorAlerts (error notifications)
- [ ] Create hooks:
  - [ ] useAgentStatus (WebSocket)
  - [ ] useRecentTasks (HTTP + WebSocket)
  - [ ] useMetrics (HTTP)
- [ ] Match PratikoAI design system exactly
- [ ] Implement mobile-responsive layouts
- [ ] Write component tests (Jest + React Testing Library)

**Acceptance Criteria**:
- [ ] Colors match PratikoAI palette exactly
- [ ] Icons match Lucide React patterns
- [ ] Mobile-friendly (tested on >375px width)
- [ ] WebSocket reconnects on disconnect
- [ ] No hydration errors

---

### Phase 4: Testing & Optimization (3 days)
**Owner**: @Clelia (test validation) + @Valerio (performance)

**Tasks**:
- [ ] Load testing (10+ concurrent WebSocket clients)
- [ ] Verify test coverage ≥49%
- [ ] Performance audit (page load < 2s)
- [ ] WebSocket latency testing (< 2s updates)
- [ ] Mobile testing (iOS Safari, Android Chrome)
- [ ] Database query optimization
- [ ] Redis caching for metrics (optional)

**Acceptance Criteria**:
- [ ] Supports 10+ concurrent dashboard viewers
- [ ] WebSocket latency < 2 seconds
- [ ] Page load < 2 seconds
- [ ] No memory leaks (tested 1 hour continuous use)

---

### Phase 5: Documentation & Deployment (2 days)
**Owner**: @Silvano (DevOps) + @Ottavio (Sprint Master)

**Tasks**:
- [ ] Update ARCHITECTURE_ROADMAP.md
- [ ] Write user documentation (how to access dashboard)
- [ ] Create deployment checklist
- [ ] Configure production environment variables
- [ ] Set up monitoring (Prometheus metrics)
- [ ] Create rollback plan

**Acceptance Criteria**:
- [ ] Documentation complete and accurate
- [ ] Production deployment successful
- [ ] Rollback plan tested
- [ ] Monitoring dashboards configured

---

## Technical Stack

### Backend
- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 15+ (with JSONB support)
- **WebSocket**: FastAPI WebSocket support
- **ORM**: SQLAlchemy 2.0+
- **Migrations**: Alembic

### Frontend
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS 4
- **Components**: Radix UI + shadcn/ui pattern
- **Icons**: Lucide React
- **State**: React hooks (no Redux needed for now)
- **HTTP Client**: fetch API (native)

### Infrastructure
- **Monitoring**: Prometheus + Grafana (already in place)
- **Logging**: Daily JSONL files in `/logs/agents/`
- **Caching**: Redis (optional, for metrics)
- **Deployment**: Docker Compose (existing setup)

---

## Security Considerations

### Authentication
- Dashboard requires authentication (same as main app)
- WebSocket connections must validate JWT token
- API endpoints protected by auth middleware

### Data Privacy
- Agent transcripts may contain PII → GDPR compliance required
- Daily logs encrypted at rest
- Automatic deletion after 30 days

### Rate Limiting
- WebSocket connections limited to 10 per user
- API endpoints: 100 requests/minute per user

---

## Future Enhancements

### V2 Features (Post-MVP)
- [ ] Agent performance analytics (charts showing tasks/hour trends)
- [ ] Task filtering (by agent, date range, status)
- [ ] Error grouping and deduplication
- [ ] Slack/email notifications for errors
- [ ] Agent health checks (heartbeat monitoring)
- [ ] Manual agent pause/resume controls
- [ ] Task replay (re-run failed tasks)

### V3 Features (Long-term)
- [ ] Multi-project support (switch between repositories)
- [ ] Agent collaboration graph (visualize agent handoffs)
- [ ] Predictive task duration (ML-based estimates)
- [ ] Custom agent metrics (user-defined KPIs)

---

## References

### Documentation
- [Claude Code Hooks](https://code.claude.com/docs/en/hooks)
- [FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)
- [Next.js App Router](https://nextjs.org/docs/app)
- [Radix UI Components](https://www.radix-ui.com/)

### Related Files
- `/Users/micky/PycharmProjects/PratikoAi-BE/WORKFLOW_IMPROVEMENT_PROPOSAL.md`
- `/Users/micky/PycharmProjects/PratikoAi-BE/.claude/agents/business-analyst.md`
- `/Users/micky/PycharmProjects/PratikoAi-BE/docs/project/subagent-assignments.md`
- `/Users/micky/WebstormProjects/PratikoAi-BE/web/tailwind.config.ts`

---

**End of Specification**

**Next Steps**:
1. Review this specification with @Egidio (Architect) for architecture approval
2. Create task in ARCHITECTURE_ROADMAP.md: `DEV-BE-XXX: Agent Monitoring Dashboard`
3. Assign to @Ottavio for sprint planning
4. Begin Phase 1 implementation with @Primo + @Ezio

**Version**: 1.0
**Last Updated**: 2025-11-27
**Maintainer**: Ottavio (Sprint Master)

export interface ChecklistItem {
  id: string;
  text: string;
  completed: boolean;
}

// ADR-036: No document storage in procedures — checkbox-based verification only
export interface Document {
  id: string;
  name: string;
  required: boolean;
  verified: boolean;
  verifiedDate?: string;
  verificationNote?: string;
}

export interface Note {
  id: string;
  text: string;
  date: string;
  attachments?: string[];
}

export interface Step {
  id: string;
  number: number;
  title: string;
  description: string;
  checklist: ChecklistItem[];
  documents: Document[];
  notes: Note[];
  completed: boolean;
}

export interface Procedura {
  id: string;
  title: string;
  description: string;
  category: string;
  totalSteps: number;
  completedSteps: number;
  progress: number;
  steps: Step[];
  clientId?: string;
  clientName?: string;
  lastUpdated?: string;
}

export interface Client {
  id: string;
  name: string;
}

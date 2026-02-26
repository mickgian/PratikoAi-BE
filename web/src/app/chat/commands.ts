export interface SlashCommand {
  name: string;
  description: string;
}

export const SLASH_COMMANDS: SlashCommand[] = [
  { name: '/utilizzo', description: 'Mostra lo stato di utilizzo e crediti' },
  { name: '/novita', description: 'Mostra le novità e note di rilascio' },
];

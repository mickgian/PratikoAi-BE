export interface SlashCommand {
  name: string;
  description: string;
}

export const SLASH_COMMANDS: SlashCommand[] = [
  {
    name: '/consigli',
    description: 'Genera un report con consigli personalizzati',
  },
  { name: '/novita', description: 'Mostra le novità e note di rilascio' },
  { name: '/procedura', description: 'Cerca e consulta procedure guidate' },
  { name: '/utilizzo', description: 'Mostra lo stato di utilizzo e crediti' },
];

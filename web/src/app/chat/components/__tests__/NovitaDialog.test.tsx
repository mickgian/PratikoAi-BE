/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { NovitaDialog } from '../NovitaDialog';
import type { ReleaseNotePublic } from '@/lib/api/release-notes';

const mockNotes: ReleaseNotePublic[] = [
  {
    version: '0.2.0',
    released_at: '2026-02-26T10:00:00Z',
    user_notes:
      'Versione 0.2.0\n\nNovità:\n- Sistema di versioning\n- Note di rilascio',
  },
  {
    version: '0.1.0',
    released_at: '2026-01-15T10:00:00Z',
    user_notes: 'Versione 0.1.0\n\nPrima release.',
  },
];

describe('NovitaDialog', () => {
  it('should render release notes list', () => {
    render(<NovitaDialog notes={mockNotes} error={null} onClose={jest.fn()} />);

    expect(screen.getByTestId('novita-dialog')).toBeInTheDocument();
    expect(screen.getByText('Novità')).toBeInTheDocument();
    expect(screen.getByText('v0.2.0')).toBeInTheDocument();
    expect(screen.getByText('v0.1.0')).toBeInTheDocument();
  });

  it('should render user_notes content', () => {
    render(<NovitaDialog notes={mockNotes} error={null} onClose={jest.fn()} />);

    expect(screen.getByText('Sistema di versioning')).toBeInTheDocument();
    expect(screen.getByText('Note di rilascio')).toBeInTheDocument();
  });

  it('should call onClose when Escape key is pressed', () => {
    const onClose = jest.fn();
    render(<NovitaDialog notes={mockNotes} error={null} onClose={onClose} />);

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('should call onClose when backdrop is clicked', () => {
    const onClose = jest.fn();
    render(<NovitaDialog notes={mockNotes} error={null} onClose={onClose} />);

    fireEvent.click(screen.getByTestId('novita-dialog'));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('should NOT call onClose when card content is clicked', () => {
    const onClose = jest.fn();
    render(<NovitaDialog notes={mockNotes} error={null} onClose={onClose} />);

    fireEvent.click(screen.getByTestId('novita-content'));

    expect(onClose).not.toHaveBeenCalled();
  });

  it('should render error message when error prop provided', () => {
    render(
      <NovitaDialog
        notes={[]}
        error="Errore nel recupero delle novità."
        onClose={jest.fn()}
      />
    );

    expect(
      screen.getByText('Errore nel recupero delle novità.')
    ).toBeInTheDocument();
  });

  it('should render empty state when no notes', () => {
    render(<NovitaDialog notes={[]} error={null} onClose={jest.fn()} />);

    expect(
      screen.getByText('Nessuna nota di rilascio disponibile.')
    ).toBeInTheDocument();
  });

  it('should show "Premi Esc per chiudere" footer', () => {
    render(<NovitaDialog notes={mockNotes} error={null} onClose={jest.fn()} />);

    expect(screen.getByText('Premi Esc per chiudere')).toBeInTheDocument();
  });
});

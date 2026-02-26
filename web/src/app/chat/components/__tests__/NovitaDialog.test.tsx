/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { NovitaDialog } from '../NovitaDialog';
import type { ReleaseNotePublic, ReleaseNote } from '@/lib/api/release-notes';

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

const mockFullNotes: ReleaseNote[] = [
  {
    version: '0.2.0',
    released_at: '2026-02-26T10:00:00Z',
    user_notes:
      'Versione 0.2.0\n\nNovità:\n- Sistema di versioning\n- Note di rilascio',
    technical_notes:
      'feat: add versioning system\nfix: correct release notes API',
  },
  {
    version: '0.1.0',
    released_at: '2026-01-15T10:00:00Z',
    user_notes: 'Versione 0.1.0\n\nPrima release.',
    technical_notes: 'Initial release with base features',
  },
];

describe('NovitaDialog - Production mode', () => {
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

  it('should NOT show technical notes or edit button in production mode', () => {
    render(<NovitaDialog notes={mockNotes} error={null} onClose={jest.fn()} />);

    expect(
      screen.queryByTestId('technical-notes-section')
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId('save-user-notes-btn')).not.toBeInTheDocument();
  });
});

describe('NovitaDialog - QA mode', () => {
  it('should show technical notes section when environment is qa', () => {
    render(
      <NovitaDialog
        notes={mockFullNotes}
        error={null}
        onClose={jest.fn()}
        environment="qa"
        onSaveUserNotes={jest.fn()}
      />
    );

    const sections = screen.getAllByTestId('technical-notes-section');
    expect(sections.length).toBe(2);
  });

  it('should display technical_notes for each version in QA', () => {
    render(
      <NovitaDialog
        notes={mockFullNotes}
        error={null}
        onClose={jest.fn()}
        environment="qa"
        onSaveUserNotes={jest.fn()}
      />
    );

    expect(screen.getByText('feat: add versioning system')).toBeInTheDocument();
  });

  it('should show editable textarea for user_notes in QA mode', () => {
    render(
      <NovitaDialog
        notes={mockFullNotes}
        error={null}
        onClose={jest.fn()}
        environment="qa"
        onSaveUserNotes={jest.fn()}
      />
    );

    const textareas = screen.getAllByTestId('user-notes-textarea');
    expect(textareas.length).toBeGreaterThan(0);
  });

  it('should allow editing user_notes in QA mode', () => {
    render(
      <NovitaDialog
        notes={mockFullNotes}
        error={null}
        onClose={jest.fn()}
        environment="qa"
        onSaveUserNotes={jest.fn()}
      />
    );

    const textarea = screen.getAllByTestId('user-notes-textarea')[0];
    fireEvent.change(textarea, { target: { value: 'Note modificate!' } });

    expect(textarea).toHaveValue('Note modificate!');
  });

  it('should show save button for each note in QA mode', () => {
    render(
      <NovitaDialog
        notes={mockFullNotes}
        error={null}
        onClose={jest.fn()}
        environment="qa"
        onSaveUserNotes={jest.fn()}
      />
    );

    const saveButtons = screen.getAllByTestId('save-user-notes-btn');
    expect(saveButtons.length).toBe(2);
  });

  it('should call onSaveUserNotes when save button is clicked', () => {
    const onSave = jest.fn();
    render(
      <NovitaDialog
        notes={mockFullNotes}
        error={null}
        onClose={jest.fn()}
        environment="qa"
        onSaveUserNotes={onSave}
      />
    );

    const saveButtons = screen.getAllByTestId('save-user-notes-btn');
    fireEvent.click(saveButtons[0]);

    expect(onSave).toHaveBeenCalledWith('0.2.0', mockFullNotes[0].user_notes);
  });

  it('should NOT show QA features in development environment', () => {
    render(
      <NovitaDialog
        notes={mockNotes}
        error={null}
        onClose={jest.fn()}
        environment="development"
      />
    );

    expect(
      screen.queryByTestId('technical-notes-section')
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId('save-user-notes-btn')).not.toBeInTheDocument();
  });
});

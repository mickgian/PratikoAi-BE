/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { DragDropZone } from '../DragDropZone';

// Mock the documents API
jest.mock('@/lib/api/documents', () => ({
  isValidFileType: jest.fn((file: File) => {
    const validTypes = ['application/pdf', 'image/jpeg', 'image/png'];
    return validTypes.includes(file.type);
  }),
}));

describe('DragDropZone', () => {
  const mockOnFilesDropped = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render children', () => {
    render(
      <DragDropZone onFilesDropped={mockOnFilesDropped}>
        <div data-testid="child-content">Child Content</div>
      </DragDropZone>
    );

    expect(screen.getByTestId('child-content')).toBeInTheDocument();
    expect(screen.getByText('Child Content')).toBeInTheDocument();
  });

  it('should show overlay when dragging files', () => {
    render(
      <DragDropZone onFilesDropped={mockOnFilesDropped}>
        <div>Content</div>
      </DragDropZone>
    );

    const zone = screen.getByTestId('drag-drop-zone');

    // Start dragging
    fireEvent.dragEnter(zone, {
      dataTransfer: { types: ['Files'] },
    });

    expect(screen.getByTestId('drag-overlay')).toBeInTheDocument();
    expect(screen.getByText('Trascina qui i file')).toBeInTheDocument();
  });

  it('should hide overlay when dragging leaves', () => {
    render(
      <DragDropZone onFilesDropped={mockOnFilesDropped}>
        <div>Content</div>
      </DragDropZone>
    );

    const zone = screen.getByTestId('drag-drop-zone');

    // Start dragging
    fireEvent.dragEnter(zone, {
      dataTransfer: { types: ['Files'] },
    });

    expect(screen.getByTestId('drag-overlay')).toBeInTheDocument();

    // Stop dragging
    fireEvent.dragLeave(zone, {
      dataTransfer: { types: ['Files'] },
    });

    expect(screen.queryByTestId('drag-overlay')).not.toBeInTheDocument();
  });

  it('should call onFilesDropped with valid files when dropped', () => {
    render(
      <DragDropZone onFilesDropped={mockOnFilesDropped}>
        <div>Content</div>
      </DragDropZone>
    );

    const zone = screen.getByTestId('drag-drop-zone');
    const validFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });

    fireEvent.drop(zone, {
      dataTransfer: {
        files: [validFile],
        types: ['Files'],
      },
    });

    expect(mockOnFilesDropped).toHaveBeenCalledWith([validFile]);
  });

  it('should filter out invalid file types', () => {
    render(
      <DragDropZone onFilesDropped={mockOnFilesDropped}>
        <div>Content</div>
      </DragDropZone>
    );

    const zone = screen.getByTestId('drag-drop-zone');
    const validFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    const invalidFile = new File(['content'], 'test.exe', { type: 'application/x-executable' });

    fireEvent.drop(zone, {
      dataTransfer: {
        files: [validFile, invalidFile],
        types: ['Files'],
      },
    });

    // Should only pass the valid file
    expect(mockOnFilesDropped).toHaveBeenCalledWith([validFile]);
  });

  it('should not call onFilesDropped if all files are invalid', () => {
    render(
      <DragDropZone onFilesDropped={mockOnFilesDropped}>
        <div>Content</div>
      </DragDropZone>
    );

    const zone = screen.getByTestId('drag-drop-zone');
    const invalidFile = new File(['content'], 'test.exe', { type: 'application/x-executable' });

    fireEvent.drop(zone, {
      dataTransfer: {
        files: [invalidFile],
        types: ['Files'],
      },
    });

    expect(mockOnFilesDropped).not.toHaveBeenCalled();
  });

  it('should hide overlay after drop', () => {
    render(
      <DragDropZone onFilesDropped={mockOnFilesDropped}>
        <div>Content</div>
      </DragDropZone>
    );

    const zone = screen.getByTestId('drag-drop-zone');

    // Start dragging
    fireEvent.dragEnter(zone, {
      dataTransfer: { types: ['Files'] },
    });

    expect(screen.getByTestId('drag-overlay')).toBeInTheDocument();

    // Drop
    const validFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    fireEvent.drop(zone, {
      dataTransfer: {
        files: [validFile],
        types: ['Files'],
      },
    });

    expect(screen.queryByTestId('drag-overlay')).not.toBeInTheDocument();
  });

  it('should not show overlay when disabled', () => {
    render(
      <DragDropZone onFilesDropped={mockOnFilesDropped} disabled>
        <div>Content</div>
      </DragDropZone>
    );

    const zone = screen.getByTestId('drag-drop-zone');

    fireEvent.dragEnter(zone, {
      dataTransfer: { types: ['Files'] },
    });

    expect(screen.queryByTestId('drag-overlay')).not.toBeInTheDocument();
  });

  it('should not call onFilesDropped when disabled', () => {
    render(
      <DragDropZone onFilesDropped={mockOnFilesDropped} disabled>
        <div>Content</div>
      </DragDropZone>
    );

    const zone = screen.getByTestId('drag-drop-zone');
    const validFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });

    fireEvent.drop(zone, {
      dataTransfer: {
        files: [validFile],
        types: ['Files'],
      },
    });

    expect(mockOnFilesDropped).not.toHaveBeenCalled();
  });

  it('should handle dragOver event without error', () => {
    render(
      <DragDropZone onFilesDropped={mockOnFilesDropped}>
        <div>Content</div>
      </DragDropZone>
    );

    const zone = screen.getByTestId('drag-drop-zone');

    // Simply verify dragOver can be called without error
    // The actual preventDefault is called by the event handler
    expect(() => {
      fireEvent.dragOver(zone, {
        dataTransfer: {
          types: ['Files'],
          dropEffect: 'copy',
        },
      });
    }).not.toThrow();
  });

  it('should show supported file types in overlay', () => {
    render(
      <DragDropZone onFilesDropped={mockOnFilesDropped}>
        <div>Content</div>
      </DragDropZone>
    );

    const zone = screen.getByTestId('drag-drop-zone');

    fireEvent.dragEnter(zone, {
      dataTransfer: { types: ['Files'] },
    });

    expect(screen.getByText(/PDF, Excel, CSV, XML, Word, Immagini/)).toBeInTheDocument();
  });

  it('should handle nested drag events correctly', () => {
    render(
      <DragDropZone onFilesDropped={mockOnFilesDropped}>
        <div data-testid="nested">
          <div data-testid="deep-nested">Nested Content</div>
        </div>
      </DragDropZone>
    );

    const zone = screen.getByTestId('drag-drop-zone');
    const nested = screen.getByTestId('nested');

    // Enter zone
    fireEvent.dragEnter(zone, {
      dataTransfer: { types: ['Files'] },
    });

    expect(screen.getByTestId('drag-overlay')).toBeInTheDocument();

    // Enter nested (counter goes to 2)
    fireEvent.dragEnter(nested, {
      dataTransfer: { types: ['Files'] },
    });

    expect(screen.getByTestId('drag-overlay')).toBeInTheDocument();

    // Leave nested (counter goes to 1)
    fireEvent.dragLeave(nested, {
      dataTransfer: { types: ['Files'] },
    });

    // Should still be visible
    expect(screen.getByTestId('drag-overlay')).toBeInTheDocument();

    // Leave zone (counter goes to 0)
    fireEvent.dragLeave(zone, {
      dataTransfer: { types: ['Files'] },
    });

    expect(screen.queryByTestId('drag-overlay')).not.toBeInTheDocument();
  });
});

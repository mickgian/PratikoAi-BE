/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { ConsigliDialog } from '../ConsigliDialog';
import type { ConsigliReport } from '@/lib/api/consigli';

const mockReport: ConsigliReport = {
  status: 'success',
  message_it: 'Report generato con successo.',
  html_report: '<html lang="it"><body><h1>Test Report</h1></body></html>',
  stats_summary: {
    total_queries: 50,
    active_days: 20,
    session_count: 10,
  },
};

describe('ConsigliDialog', () => {
  it('should render loading state', () => {
    const onClose = jest.fn();
    render(
      <ConsigliDialog
        data={null}
        error={null}
        loading={true}
        onClose={onClose}
      />
    );

    expect(screen.getByTestId('consigli-dialog')).toBeInTheDocument();
    expect(screen.getByText(/generazione report/i)).toBeInTheDocument();
  });

  it('should render error message', () => {
    const onClose = jest.fn();
    render(
      <ConsigliDialog
        data={null}
        error="Errore nel recupero del report"
        loading={false}
        onClose={onClose}
      />
    );

    expect(screen.getByText(/errore nel recupero/i)).toBeInTheDocument();
  });

  it('should render insufficient data message', () => {
    const onClose = jest.fn();
    const insufficientData: ConsigliReport = {
      status: 'insufficient_data',
      message_it: 'Non ci sono ancora dati sufficienti.',
      html_report: null,
      stats_summary: null,
    };
    render(
      <ConsigliDialog
        data={insufficientData}
        error={null}
        loading={false}
        onClose={onClose}
      />
    );

    expect(screen.getByText(/dati sufficienti/i)).toBeInTheDocument();
  });

  it('should render error status from backend', () => {
    const onClose = jest.fn();
    const errorReport: ConsigliReport = {
      status: 'error',
      message_it: 'Errore nella generazione del report. Riprova più tardi.',
      html_report: null,
      stats_summary: null,
    };
    render(
      <ConsigliDialog
        data={errorReport}
        error={null}
        loading={false}
        onClose={onClose}
      />
    );

    expect(
      screen.getByText(/errore nella generazione del report/i)
    ).toBeInTheDocument();
  });

  it('should render report iframe when successful', () => {
    const onClose = jest.fn();
    render(
      <ConsigliDialog
        data={mockReport}
        error={null}
        loading={false}
        onClose={onClose}
      />
    );

    expect(screen.getByTestId('consigli-iframe')).toBeInTheDocument();
    expect(screen.getByTestId('download-report')).toBeInTheDocument();
  });

  it('should call onClose when Escape key is pressed', () => {
    const onClose = jest.fn();
    render(
      <ConsigliDialog
        data={mockReport}
        error={null}
        loading={false}
        onClose={onClose}
      />
    );

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('should call onClose when backdrop is clicked', () => {
    const onClose = jest.fn();
    render(
      <ConsigliDialog
        data={mockReport}
        error={null}
        loading={false}
        onClose={onClose}
      />
    );

    fireEvent.click(screen.getByTestId('consigli-dialog'));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('should call onClose when close button is clicked', () => {
    const onClose = jest.fn();
    render(
      <ConsigliDialog
        data={mockReport}
        error={null}
        loading={false}
        onClose={onClose}
      />
    );

    fireEvent.click(screen.getByTestId('close-consigli'));

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

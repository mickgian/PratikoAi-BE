/**
 * @file VersionBadge Component Tests
 * @description TDD RED phase - tests for the version badge in footer
 */

import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { VersionBadge } from '../VersionBadge';

describe('VersionBadge Component', () => {
  it('should render version text', () => {
    render(<VersionBadge version="0.2.0" />);
    expect(screen.getByText(/v0\.2\.0/)).toBeInTheDocument();
  });

  it('should render a link to novita page', () => {
    render(<VersionBadge version="0.2.0" />);
    const link = screen.getByRole('link', { name: /novità/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/novita');
  });

  it('should render nothing when version is empty', () => {
    const { container } = render(<VersionBadge version="" />);
    expect(container.textContent).toBe('');
  });
});

/**
 * @file VersionBadge Component Tests
 * @description Tests for the version badge in footer
 */

import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { VersionBadge } from '../VersionBadge';

describe('VersionBadge Component', () => {
  it('should render version text', () => {
    render(<VersionBadge version="0.2.0" />);
    expect(screen.getByText(/v0\.2\.0/)).toBeInTheDocument();
  });

  it('should render nothing when version is empty', () => {
    const { container } = render(<VersionBadge version="" />);
    expect(container.textContent).toBe('');
  });
});

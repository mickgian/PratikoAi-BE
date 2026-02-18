import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from '@/components/ui/button';

describe('Button', () => {
  test('renders button with text', () => {
    render(<Button>Click me</Button>);

    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
  });

  test('handles click events', async () => {
    const handleClick = jest.fn();
    const user = userEvent.setup();

    render(<Button onClick={handleClick}>Click me</Button>);

    const button = screen.getByRole('button', { name: /click me/i });
    await user.click(button);

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  test('applies default variant and size classes', () => {
    render(<Button>Default Button</Button>);

    const button = screen.getByRole('button', { name: /default button/i });
    expect(button).toHaveClass('bg-primary', 'text-primary-foreground', 'h-9');
  });

  test('applies variant classes correctly', () => {
    const { rerender } = render(
      <Button variant="destructive">Destructive</Button>
    );

    let button = screen.getByRole('button');
    expect(button).toHaveClass('bg-destructive', 'text-white');

    rerender(<Button variant="outline">Outline</Button>);
    button = screen.getByRole('button');
    expect(button).toHaveClass('border', 'bg-background');

    rerender(<Button variant="ghost">Ghost</Button>);
    button = screen.getByRole('button');
    expect(button).toHaveClass('hover:bg-accent');
  });

  test('applies size classes correctly', () => {
    const { rerender } = render(<Button size="sm">Small</Button>);

    let button = screen.getByRole('button');
    expect(button).toHaveClass('h-8');

    rerender(<Button size="lg">Large</Button>);
    button = screen.getByRole('button');
    expect(button).toHaveClass('h-10');

    rerender(<Button size="icon">Icon</Button>);
    button = screen.getByRole('button');
    expect(button).toHaveClass('size-9');
  });

  test('applies custom className', () => {
    render(<Button className="custom-class">Custom</Button>);

    const button = screen.getByRole('button');
    expect(button).toHaveClass('custom-class');
  });

  test('handles disabled state', () => {
    render(<Button disabled>Disabled</Button>);

    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(button).toHaveClass('disabled:opacity-50');
  });

  test('renders as child when asChild is true', () => {
    render(
      <Button asChild>
        <a href="/test">Link Button</a>
      </Button>
    );

    const link = screen.getByRole('link', { name: /link button/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/test');
    // Should have button styling but be a link element
    expect(link).toHaveClass('bg-primary', 'text-primary-foreground');
  });

  test('passes through button props', () => {
    render(
      <Button type="submit" id="submit-btn" aria-label="Submit form">
        Submit
      </Button>
    );

    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('type', 'submit');
    expect(button).toHaveAttribute('id', 'submit-btn');
    expect(button).toHaveAttribute('aria-label', 'Submit form');
  });

  test('has correct data attribute', () => {
    render(<Button>Test</Button>);

    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('data-slot', 'button');
  });

  test('renders with different content types', () => {
    const { rerender } = render(<Button>Text content</Button>);

    let button = screen.getByRole('button');
    expect(button).toHaveTextContent('Text content');

    rerender(
      <Button>
        <span>Nested content</span>
      </Button>
    );

    button = screen.getByRole('button');
    expect(button).toContainHTML('<span>Nested content</span>');
  });

  test('handles focus and keyboard navigation', async () => {
    const user = userEvent.setup();

    render(<Button>Focusable</Button>);

    const button = screen.getByRole('button');

    // Tab to focus the button
    await user.tab();
    expect(button).toHaveFocus();

    // Press Enter to activate
    const handleClick = jest.fn();
    button.onclick = handleClick;
    await user.keyboard('{Enter}');
    expect(handleClick).toHaveBeenCalled();
  });

  test('handles space key activation', async () => {
    const handleClick = jest.fn();
    const user = userEvent.setup();

    render(<Button onClick={handleClick}>Space Test</Button>);

    const button = screen.getByRole('button');
    button.focus();

    await user.keyboard(' ');
    expect(handleClick).toHaveBeenCalled();
  });
});

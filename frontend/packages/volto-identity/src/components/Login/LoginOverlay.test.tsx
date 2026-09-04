import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '../../testing';
import React from 'react';

import LoginOverlay, { useDismissibleError } from './LoginOverlay';

describe('LoginOverlay', () => {
  it('announces a wait without interrupting', () => {
    // A wait is a status: something is happening and the reader may keep
    // reading. An alert would interrupt them to say so.
    render(<LoginOverlay message="Taking you to Dex…" />);

    expect(screen.getByRole('status').textContent).toContain('Dex');
    expect(document.querySelector('.identity-spinner')).toBeTruthy();
  });

  it('announces a refusal as one', () => {
    render(<LoginOverlay error message="That did not work." />);

    expect(screen.getByRole('alert').textContent).toContain('did not work');
  });

  it('draws no spinner on a refusal', () => {
    // Nothing is happening, which is the whole message.
    render(<LoginOverlay error message="That did not work." />);

    expect(document.querySelector('.identity-spinner')).toBeNull();
  });

  it('offers no way out of a wait', () => {
    // It is not the reader's to end, and a button would say otherwise.
    render(<LoginOverlay message="Signing in" onDismiss={vi.fn()} />);

    expect(screen.queryByRole('button', { name: 'Close' })).toBeNull();
  });

  it('offers a way out of a refusal', () => {
    const onDismiss = vi.fn();
    render(
      <LoginOverlay error message="That did not work." onDismiss={onDismiss} />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Close' }));

    expect(onDismiss).toHaveBeenCalled();
  });

  it('has no dismiss button when nothing can be dismissed to', () => {
    render(<LoginOverlay error message="That did not work." />);

    expect(screen.queryByRole('button', { name: 'Close' })).toBeNull();
  });
});

/** A host for the hook, since a hook cannot be rendered on its own. */
const Host: React.FC<{ error: unknown }> = ({ error }) => {
  const [visible, dismiss] = useDismissibleError(error);
  return visible ? (
    <button type="button" onClick={dismiss}>
      showing
    </button>
  ) : (
    <span>hidden</span>
  );
};

describe('useDismissibleError', () => {
  it('shows a refusal that has not been dismissed', () => {
    render(<Host error={{ status: 401 }} />);

    expect(screen.getByText('showing')).toBeTruthy();
  });

  it('shows nothing when there is no refusal', () => {
    render(<Host error={null} />);

    expect(screen.getByText('hidden')).toBeTruthy();
  });

  it('hides the one that was dismissed', () => {
    render(<Host error={{ status: 401 }} />);

    fireEvent.click(screen.getByText('showing'));

    expect(screen.getByText('hidden')).toBeTruthy();
  });

  it('shows the next one anyway', () => {
    // Dismissing is about the refusal that was read, not about refusals in
    // general -- a second wrong password has to say so again.
    const { rerender } = render(<Host error={{ status: 401 }} />);
    fireEvent.click(screen.getByText('showing'));

    rerender(<Host error={{ status: 401 }} />);

    expect(screen.getByText('showing')).toBeTruthy();
  });
});

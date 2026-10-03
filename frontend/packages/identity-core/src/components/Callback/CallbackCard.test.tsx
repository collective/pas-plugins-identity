import { describe, expect, it } from 'vitest';
import React from 'react';

import { render, screen } from '../../testing';
import CallbackCard from './CallbackCard';

describe('CallbackCard', () => {
  it('says it is signing in while there is no outcome', () => {
    render(<CallbackCard retryHref="/login" />);

    expect(screen.getByRole('status').textContent).toBe('Signing you in…');
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('says it is confirming while it links', () => {
    render(<CallbackCard linking retryHref="/login" />);

    expect(screen.getByRole('status').textContent).toBe(
      'Confirming your address…',
    );
  });

  it.each([
    ['refused', 'The provider refused the sign-in.'],
    ['incomplete', 'This sign-in link is incomplete.'],
    ['invalid', 'That sign-in link is no longer valid. Please start again.'],
    ['unavailable', 'That sign-in option is not available right now.'],
  ] as const)('explains a %s sign-in', (failure, text) => {
    render(<CallbackCard failure={failure} retryHref="/login" />);

    expect(screen.getByRole('alert').textContent).toBe(text);
    expect(screen.queryByRole('status')).toBeNull();
  });

  it('leads back to where it is told', () => {
    render(<CallbackCard failure="refused" retryHref="/login?choose=1" />);

    const link = screen.getByRole('link', { name: 'Back to sign-in options' });
    expect(link.getAttribute('href')).toBe('/login?choose=1');
  });

  it('sits in the login card', () => {
    const { container } = render(<CallbackCard retryHref="/login" />);

    expect(
      container.querySelector('.loginForm .identity-callback'),
    ).toBeTruthy();
  });
});

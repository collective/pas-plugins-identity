import { describe, expect, it } from 'vitest';
import { render, screen } from '../../testing';
import React from 'react';

import Count from './Count';

describe('Count', () => {
  it('shows the figure and its label', () => {
    const { container } = render(<Count value={42} label="members" />);

    expect(container.textContent).toBe('42 members');
  });

  it('formats the figure for the locale', () => {
    render(<Count value={1234} label="members" />);

    expect(screen.getByText('1,234')).toBeTruthy();
  });

  it('sets the figure apart from the words', () => {
    render(<Count value={42} label="members" />);

    expect(screen.getByText('42').className).toBe('identity-count__value');
  });

  it('is primary unless told otherwise', () => {
    const { container } = render(<Count value={42} label="members" />);

    expect(container.firstElementChild?.className).toBe('identity-count');
  });

  it('can step back beside another count', () => {
    const { container } = render(
      <Count value={12} label="directly" secondary />,
    );

    expect(container.firstElementChild?.className).toContain(
      'identity-count--secondary',
    );
  });
});

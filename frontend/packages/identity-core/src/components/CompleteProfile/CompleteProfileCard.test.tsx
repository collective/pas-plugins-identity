import { describe, expect, it } from 'vitest';
import React from 'react';
import { render, screen } from '../../testing';

import CompleteProfileCard from './CompleteProfileCard';

describe('CompleteProfileCard', () => {
  it('names the fields the profile is missing', () => {
    render(
      <CompleteProfileCard
        held
        missing={['Organisation', 'Country']}
        editHref="/@@edit/profiles/alice"
      />,
    );

    expect(screen.getByRole('status').textContent).toBe(
      'Please fill in Organisation, Country before you can continue.',
    );
  });

  it('says so in general when the backend named none', () => {
    render(<CompleteProfileCard held missing={[]} editHref="/x" />);

    expect(screen.getByRole('status').textContent).toMatch(/a few more/);
  });

  it('leads to the edit form', () => {
    render(
      <CompleteProfileCard
        held
        missing={[]}
        editHref="/@@edit/profiles/alice"
      />,
    );

    expect(
      screen.getByText('Edit your profile').closest('a')?.getAttribute('href'),
    ).toBe('/@@edit/profiles/alice');
  });

  it('lets a complete profile carry on', () => {
    render(
      <CompleteProfileCard
        held={false}
        missing={[]}
        editHref={null}
        continueHref="/news"
      />,
    );

    expect(screen.getByRole('status').textContent).toBe(
      'Your profile is complete.',
    );
    expect(
      screen.getByText('Continue').closest('a')?.getAttribute('href'),
    ).toBe('/news');
  });
});

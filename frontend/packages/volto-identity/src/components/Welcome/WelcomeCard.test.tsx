import { describe, expect, it } from 'vitest';
import React from 'react';
import { render, screen } from '../../testing';

import WelcomeCard from './WelcomeCard';

const EVERYTHING = {
  greeting: 'Hello Alice Liddell!',
  profile: { to: '/identity-profiles/alice', label: 'Alice Liddell' },
  email: { address: 'alice@example.com', verified: true, preferred: true },
  provider: 'GitHub',
  lastLogin: 'September 10, 2026',
};

/**
 * Read the summary as the pairs it shows.
 *
 * @returns Each term with its description.
 */
function summary(): Record<string, string> {
  const terms = Array.from(document.querySelectorAll('dt'));
  return Object.fromEntries(
    terms.map((dt) => [dt.textContent, dt.nextElementSibling?.textContent]),
  );
}

describe('WelcomeCard', () => {
  it('heads the login card with the greeting as it was given', () => {
    render(<WelcomeCard {...EVERYTHING} />);

    expect(
      document.querySelector('.identity-login-card .title')?.textContent,
    ).toBe('Hello Alice Liddell!');
  });

  it('puts the summary in the body of the card', () => {
    render(<WelcomeCard {...EVERYTHING} />);

    expect(
      document.querySelector('.identity-login-card .form dl'),
    ).toBeTruthy();
  });

  it('prints every line it is given', () => {
    render(<WelcomeCard {...EVERYTHING} />);

    expect(summary()).toEqual({
      'Your profile': 'Alice Liddell',
      'Preferred email': 'alice@example.com (verified)',
      'Authenticated with': 'GitHub',
      'Last login': 'September 10, 2026',
    });
  });

  it('links to the profile inside the site', () => {
    render(<WelcomeCard {...EVERYTHING} />);

    expect(
      screen.getByRole('link', { name: 'Alice Liddell' }).getAttribute('href'),
    ).toBe('/identity-profiles/alice');
  });

  it('says so when the address is not verified', () => {
    render(
      <WelcomeCard
        {...EVERYTHING}
        email={{ ...EVERYTHING.email, verified: false }}
      />,
    );

    expect(summary()['Preferred email']).toBe(
      'alice@example.com (not verified)',
    );
  });

  it('leaves out a line with nothing to say', () => {
    render(<WelcomeCard {...EVERYTHING} provider={null} lastLogin={null} />);

    expect(Object.keys(summary())).toEqual(['Your profile', 'Preferred email']);
  });

  it('is headed "Welcome" when there is no greeting', () => {
    // A card with a blank heading reads as one that failed to load.
    render(<WelcomeCard greeting="" />);

    expect(
      document.querySelector('.identity-login-card .title')?.textContent,
    ).toBe('Welcome');
  });

  it('prints no empty summary', () => {
    render(<WelcomeCard greeting="Hello" />);

    expect(document.querySelector('dl')).toBeNull();
  });
});

import { describe, expect, it } from 'vitest';
import { render, screen } from '../../testing';
import React from 'react';

import ProfileView, { pictureUrl } from './ProfileView';

const CONTENT = {
  '@id': '/identity-profiles/alice',
  title: 'Alice Liddell',
  fullname: 'Alice Liddell',
  description: 'Reads a lot.',
  image: {
    download: '/identity-profiles/alice/@@images/image',
    scales: {
      preview: { download: '/identity-profiles/alice/@@images/image/preview' },
    },
  },
};

describe('pictureUrl', () => {
  it('prefers a scale over the original', () => {
    // An uploaded portrait is whatever the camera produced, and a page that
    // renders it at full size downloads megabytes to draw a thumbnail.
    expect(pictureUrl(CONTENT.image)).toContain('/preview');
  });

  it('falls back to the original when there is no scale', () => {
    expect(pictureUrl({ download: '/x' })).toBe('/x');
  });

  it('answers nothing for a profile with no picture', () => {
    expect(pictureUrl(null)).toBeNull();
  });
});

describe('ProfileView', () => {
  it('shows the full name as the heading', () => {
    render(<ProfileView content={CONTENT} />);

    expect(screen.getByRole('heading').textContent).toBe('Alice Liddell');
  });

  it('shows the biography', () => {
    render(<ProfileView content={CONTENT} />);

    expect(screen.getByText('Reads a lot.')).toBeTruthy();
  });

  it('shows the picture, labelled with the name', () => {
    render(<ProfileView content={CONTENT} />);

    const image = screen.getByAltText('Alice Liddell') as HTMLImageElement;
    expect(image.getAttribute('src')).toContain('/preview');
  });

  it('renders no image element when there is no picture', () => {
    render(<ProfileView content={{ ...CONTENT, image: null }} />);

    expect(document.querySelector('img')).toBeNull();
  });

  it('falls back to the computed title when there is no full name', () => {
    // The backend computes `title` from the full name and then the login, so
    // it is never empty -- which makes it the honest fallback.
    render(<ProfileView content={{ ...CONTENT, fullname: '' }} />);

    expect(screen.getByRole('heading').textContent).toBe('Alice Liddell');
  });

  it('never publishes an address', () => {
    // The field carries a read permission of its own, but a view that
    // rendered it when it happened to be there would publish an address on a
    // page whose URL is guessable from a userid.
    render(
      <ProfileView
        content={{ ...CONTENT, email: 'alice@example.com' } as any}
      />,
    );

    expect(screen.queryByText(/alice@example.com/)).toBeNull();
  });
});

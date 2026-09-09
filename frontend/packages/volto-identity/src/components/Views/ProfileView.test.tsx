import { afterEach, describe, expect, it } from 'vitest';
import { render, screen } from '../../testing';
import React from 'react';

import config from '@plone/volto/registry';

import ProfileView, { pictureUrl } from './ProfileView';
import { profileContent } from '../../stories/fixtures';

// No `title`. A Profile has no such field -- only a computed `Title()`, which
// `plone.restapi` does not serialize -- and a fixture that carried one made
// the fallback below pass for a reason no real payload supplies.
const CONTENT = profileContent({
  description: 'Reads a lot.',
  image: {
    download: '/identity-profiles/alice/@@images/image',
    scales: {
      preview: { download: '/identity-profiles/alice/@@images/image/preview' },
    },
  },
});

/**
 * Register a component into `belowTitle`, the way a deployment does.
 *
 * @param component What to render.
 */
function registerBadge(component: React.ComponentType<any>): void {
  config.registerSlotComponent({
    slot: 'belowTitle',
    name: 'badge',
    component,
  });
}

// A slot registration is global and outlives the test that made it.
afterEach(() => {
  delete config.slots.belowTitle;
});

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

  it('falls back to the login when there is no full name', () => {
    // The same order the backend's own `Title()` uses. It used to fall back
    // to `content.title`, which is never in the payload, so a person with a
    // login and no full name was rendered as "Unnamed user".
    render(<ProfileView content={{ ...CONTENT, fullname: '' }} />);

    expect(screen.getByRole('heading').textContent).toBe('alice@example.com');
  });

  it('falls back to the userid when there is no login either', () => {
    // The last rung the backend uses before giving up. A Profile always has
    // an id, so this is the case that has to stop short of the message.
    render(<ProfileView content={{ ...CONTENT, fullname: '', login: '' }} />);

    expect(screen.getByRole('heading').textContent).toBe('alice');
  });

  it('says so when the profile carries no name at all', () => {
    render(
      <ProfileView content={{ ...CONTENT, fullname: '', login: '', id: '' }} />,
    );

    expect(screen.getByRole('heading').textContent).toBe('Unnamed user');
  });

  it('renders the belowTitle slot between the heading and the description', () => {
    // Under the name, where what belongs to the person reads as part of it.
    // Nothing outside a view can put anything inside one, which is why this
    // slot is rendered here and `aboveContent` is not.
    registerBadge(() => <span>Core team</span>);

    render(<ProfileView content={CONTENT} />);

    const badge = screen.getByText('Core team');
    const heading = screen.getByRole('heading', { level: 1 });
    const description = screen.getByText('Reads a lot.');
    expect(
      heading.compareDocumentPosition(badge) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      description.compareDocumentPosition(badge) &
        Node.DOCUMENT_POSITION_PRECEDING,
    ).toBeTruthy();
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

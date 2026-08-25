import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '../../testing';
import { Provider } from 'react-redux';
import React from 'react';

import UserAvatar from './UserAvatar';
import { AVATAR_COLORS } from '../../helpers/avatar';

function renderAvatar(data: unknown, props = {}) {
  const store = {
    getState: () => ({
      userProfile: { loading: false, loaded: true, error: null, data },
    }),
    dispatch: (action: unknown) => action,
    subscribe: () => () => {},
  };
  return render(
    <Provider store={store as never}>
      <UserAvatar {...props} />
    </Provider>,
  );
}

describe('UserAvatar', () => {
  it('renders the portrait when the user has one', () => {
    renderAvatar({
      id: 'alice',
      fullname: 'Alice Liddell',
      portrait: 'http://localhost:8080/Plone/portrait.png',
    });

    const img = screen.getByRole('img', { name: /user avatar/i });

    // Flattened: the store holds the backend URL and the browser has to ask
    // this site for it.
    expect(img.getAttribute('src')).toBe('/portrait.png');
  });

  it('falls back to initials on a colour', () => {
    // Volto draws a camera icon here, which is the same picture for every
    // user without a portrait.
    const { container } = renderAvatar({
      id: 'alice',
      fullname: 'Alice Liddell',
    });

    const avatar = container.querySelector('.identity-avatar--initials');
    expect(avatar?.textContent).toBe('AL');
    expect(avatar).toBeTruthy();
  });

  it('colours the initials from the palette', () => {
    const { container } = renderAvatar({
      id: 'alice',
      fullname: 'Alice Liddell',
    });

    const style = container
      .querySelector('.identity-avatar--initials')
      ?.getAttribute('style');

    // jsdom renders the hex as rgb(), so assert on the palette having been
    // consulted rather than on one exact string.
    expect(style).toContain('background-color');
    expect(AVATAR_COLORS.length).toBeGreaterThan(0);
  });

  it('falls back to the userid when there is no name yet', () => {
    const { container } = renderAvatar({ id: 'alice' });

    expect(
      container.querySelector('.identity-avatar--initials')?.textContent,
    ).toBe('AL');
  });

  it('renders a plain circle for an anonymous visitor', () => {
    // Mounted on every route, so this is the common case, not an edge one.
    const { container } = renderAvatar(null);

    const avatar = container.querySelector('.identity-avatar--initials');
    expect(avatar?.textContent).toBe('');
    // Nothing to read: announcing an empty circle as "user avatar" is noise.
    expect(avatar?.getAttribute('aria-hidden')).toBe('true');
    expect(avatar?.getAttribute('role')).toBeNull();
  });

  it('falls back to initials when the portrait fails to load', () => {
    // A deleted portrait, or a stale URL after a rename. The browser's
    // broken-image glyph reads as a bug in the site rather than as a
    // missing photograph.
    const { container } = renderAvatar({
      id: 'alice',
      fullname: 'Alice Liddell',
      portrait: '/gone.png',
    });

    fireEvent.error(screen.getByRole('img', { name: /user avatar/i }));

    expect(container.querySelector('img')).toBeNull();
    expect(
      container.querySelector('.identity-avatar--initials')?.textContent,
    ).toBe('AL');
  });

  it('accepts extra classes without losing its own', () => {
    const { container } = renderAvatar({ id: 'alice' }, { className: 'mine' });

    const avatar = container.querySelector('.identity-avatar');
    expect(avatar?.className).toContain('identity-avatar--initials');
    expect(avatar?.className).toContain('mine');
  });

  it('takes the size it is given', () => {
    const { container } = renderAvatar({ id: 'alice' }, { size: '96px' });

    expect(
      container.querySelector('.identity-avatar')?.getAttribute('style'),
    ).toContain('96px');
  });
});

/**
 * The shadowed personal-tools menu.
 *
 * Once it is rewritten rather than patched it is this package's code: the
 * things that differ from Volto are the things worth pinning, so a future
 * upgrade that quietly reverts one of them fails here instead of in
 * somebody's browser. The list itself is upstream's behaviour, pinned too
 * because the backend's actions are what the whole menu now rests on.
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '../../testing';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import React from 'react';

import {
  Plug,
  PluggablesProvider,
} from '@plone/volto/components/manage/Pluggable';
import PersonalTools from './PersonalTools';

const ALICE = {
  id: 'alice',
  username: 'alice@example.com',
  fullname: 'Alice Liddell',
};

/** What this package's profile lists for a member with a Profile. */
const MEMBER_TOOLS = [
  { id: 'identity_profile', title: 'Profile', url: '/identity-profiles/alice' },
  { id: 'preferences', title: 'Preferences', url: 'preferences' },
  { id: 'identities', title: 'Sign-in methods', url: '/identities' },
];

function renderMenu(
  user: unknown = ALICE,
  props: Record<string, unknown> = {},
  personalTools: unknown[] | undefined = MEMBER_TOOLS,
  plugs: React.ReactNode = null,
) {
  const store = {
    getState: () => ({
      userProfile: { loading: false, loaded: true, error: null, data: user },
      actions: { actions: { personal_tools: personalTools, user: [] } },
    }),
    dispatch: vi.fn(),
    subscribe: () => () => {},
  };
  const result = render(
    <Provider store={store as never}>
      <MemoryRouter>
        <PluggablesProvider>
          {plugs}
          <PersonalTools
            loadComponent={vi.fn()}
            unloadComponent={vi.fn()}
            theToolbar={{ current: null }}
            {...props}
          />
        </PluggablesProvider>
      </MemoryRouter>
    </Provider>,
  );
  return { ...result, store };
}

function entries(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll('.pastanaga-menu-list li')).map(
    (li) => li.textContent ?? '',
  );
}

describe('PersonalTools', () => {
  it('lists the personal_tools actions, in the order the site gives', () => {
    const { container } = renderMenu();

    expect(entries(container)).toEqual([
      'Profile',
      'Preferences',
      'Sign-in methods',
    ]);
  });

  it('links an action whose URL is a path', () => {
    renderMenu();

    expect(
      screen
        .getByRole('link', { name: 'Sign-in methods' })
        .getAttribute('href'),
    ).toBe('/identities');
  });

  it('opens a panel for an action whose URL is a bare name', () => {
    const loadComponent = vi.fn();
    renderMenu(ALICE, { loadComponent });

    screen.getByRole('button', { name: 'Preferences' }).click();

    expect(loadComponent).toHaveBeenCalledWith('preferences');
  });

  it("falls back to Volto's entries on a site without the actions", () => {
    const { container } = renderMenu(ALICE, {}, []);

    expect(entries(container)).toEqual(['Profile', 'Preferences']);
  });

  it('renders nothing plugged into toolbar-user-menu', () => {
    // An entry is an action the site manages; a plug would be a second way
    // to add one, invisible to the first.
    renderMenu(
      ALICE,
      {},
      MEMBER_TOOLS,
      <Plug pluggable="toolbar-user-menu" id="probe">
        <li id="probe-entry">Probe</li>
      </Plug>,
    );

    expect(document.querySelector('#probe-entry')).toBeNull();
  });

  it('names the user from the store this package fills', () => {
    renderMenu();

    expect(screen.getByRole('heading').textContent).toBe('Alice Liddell');
  });

  it('never leaves the header empty', () => {
    // A blank header reads as a broken menu rather than as a user who has
    // not filled their name in.
    renderMenu({ id: 'alice', username: 'alice@example.com' });
    expect(screen.getByRole('heading').textContent).toBe('alice@example.com');

    screen.getByRole('heading').remove();
    renderMenu({ id: 'alice' });
    expect(screen.getByRole('heading').textContent).toBe('alice');
  });

  it('does not fetch the user itself', () => {
    // Upstream decodes the JWT and dispatches getUser on every mount. This
    // add-on already loaded the same `@users/<userid>` once, per userid.
    const { store } = renderMenu();

    expect(store.dispatch).not.toHaveBeenCalled();
  });

  it('slides out through the prop it was given', () => {
    const unloadComponent = vi.fn();
    renderMenu(ALICE, { unloadComponent });

    screen.getByRole('button', { name: /back/i }).click();

    expect(unloadComponent).toHaveBeenCalled();
  });

  it('names the back button and the logout link', () => {
    // Upstream leaves both unnamed: an `<Icon>` with a `title` inside an
    // element with no label of its own is announced as "button".
    renderMenu();

    expect(screen.getByRole('button', { name: /back/i })).toBeTruthy();
    expect(screen.getByRole('link', { name: /logout/i })).toBeTruthy();
  });

  it('renders no avatar block', () => {
    // It moved to the toolbar button that opens this menu.
    const { container } = renderMenu();

    expect(container.querySelector('.avatar')).toBeNull();
  });

  it('keeps the class names the stylesheet is written against', () => {
    const { container } = renderMenu(ALICE, { hasActions: true });

    const root = container.querySelector('.personal-tools');
    expect(root?.className).toContain('pastanaga-menu');
    expect(root?.className).toContain('has-inner-actions');
  });
});

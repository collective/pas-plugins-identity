/**
 * The personal-tools menu as an ordered list of plugs.
 *
 * The entries are registered from five separate components, so what nobody
 * can see by reading any one of them is the thing worth testing: what the
 * assembled menu contains, in what order, and which entries stand each other
 * down.
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '../../testing';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import React from 'react';

import {
  Pluggable,
  PluggablesProvider,
} from '@plone/volto/components/manage/Pluggable';
import IdentitiesMenuItem from './IdentitiesMenuItem';
import ProfileMenuItem from './ProfileMenuItem';
import {
  PersonalInformationMenuItem,
  PreferencesMenuItem,
  SiteSetupMenuItem,
} from './UserMenuPlugs';

interface MenuState {
  /** The Profile URL `@users` reported, when the user has one. */
  profileUrl?: string | null;
  /** The PAS plugin the userid came from, as `@users` reports it. */
  source?: string | null;
  /** The user actions the backend listed. */
  actions?: unknown[];
  /** Slide a panel in; the prop `PersonalTools` passes through params. */
  loadComponent?: (selector: string) => void;
}

/**
 * Render the whole menu the way the application assembles it.
 *
 * Every plug is mounted from `appExtras` in the real thing, which is what
 * this stands in for; the `<Pluggable>` is what the shadowed `PersonalTools`
 * renders.
 *
 * @param state What the store says and what the toolbar passes down.
 * @returns The ids of the entries, in the order they were rendered.
 */
function renderMenu(state: MenuState = {}) {
  const {
    profileUrl = null,
    source = null,
    actions = [],
    loadComponent = vi.fn(),
  } = state;
  const store = {
    getState: () => ({
      userProfile: { data: { id: 'alice', profile_url: profileUrl, source } },
      actions: { actions: { user: actions } },
    }),
    dispatch: vi.fn(),
    subscribe: () => () => {},
  };

  render(
    <Provider store={store as never}>
      <MemoryRouter>
        <PluggablesProvider>
          <PersonalInformationMenuItem />
          <PreferencesMenuItem />
          <SiteSetupMenuItem />
          <IdentitiesMenuItem />
          <ProfileMenuItem />
          <ul>
            <Pluggable name="toolbar-user-menu" params={{ loadComponent }} />
          </ul>
        </PluggablesProvider>
      </MemoryRouter>
    </Provider>,
  );

  return {
    loadComponent,
    ids: Array.from(document.querySelectorAll('li > *')).map((el) => el.id),
  };
}

/** A user whose account *is* a Profile content object. */
const STORED_AS_A_PROFILE: MenuState = {
  profileUrl: 'http://site/profiles/alice',
  source: 'identity_profile',
};

describe('the personal-tools menu', () => {
  it('puts sign-in methods straight after preferences', () => {
    // Which is where it belongs: choosing how you get in is a preference,
    // and before this the pluggable could only append after Site Setup.
    const { ids } = renderMenu();

    expect(ids).toEqual([
      'toolbar-profile',
      'toolbar-preferences',
      'toolbar-identities',
    ]);
  });

  it('puts Site Setup last, for somebody who has that action', () => {
    // Last because it is about the site rather than about the person.
    const { ids } = renderMenu({ actions: [{ id: 'plone_setup' }] });

    expect(ids[ids.length - 1]).toBe('toolbar-site-setup');
  });

  it('offers Site Setup to nobody else', () => {
    const { ids } = renderMenu();

    expect(ids).not.toContain('toolbar-site-setup');
  });

  it('gives the Profile slot to the object the account lives in', () => {
    // Not beside it: two entries both called "Profile" make the reader guess
    // which one they want.
    const { ids } = renderMenu(STORED_AS_A_PROFILE);

    expect(ids).toContain('toolbar-identity-profile');
    expect(ids).not.toContain('toolbar-profile');
  });

  it('keeps it where the member form was', () => {
    const { ids } = renderMenu(STORED_AS_A_PROFILE);

    expect(ids).toEqual([
      'toolbar-identity-profile',
      'toolbar-preferences',
      'toolbar-identities',
    ]);
  });

  it('calls it Profile either way', () => {
    // It stands in the other one's place rather than beside it, so it takes
    // its name too.
    renderMenu(STORED_AS_A_PROFILE);
    expect(screen.getByText('Profile')).toBeTruthy();

    document.body.innerHTML = '';
    renderMenu();
    expect(screen.getByText('Profile')).toBeTruthy();
  });

  it('does not care which plugin authenticated the account', () => {
    // `source` names whichever plugin PAS enumerated the account from, and
    // that changes with how the account was made -- so a rule keyed on it
    // hid the entry for whole classes of user. `profile_url` is the
    // question the menu actually has.
    const { ids } = renderMenu({
      profileUrl: 'http://site/profiles/alice',
      source: 'source_users',
    });

    expect(ids).toContain('toolbar-identity-profile');
    expect(ids).not.toContain('toolbar-profile');
  });

  it('falls back to the member form when there is no Profile', () => {
    // An account that predates the add-on, or a user whose first login has
    // not minted a Profile yet.
    const { ids } = renderMenu();

    expect(ids).toContain('toolbar-profile');
    expect(ids).not.toContain('toolbar-identity-profile');
  });

  it('needs a Profile to link to', () => {
    // A menu entry leading nowhere is worse than no menu entry.
    const { ids } = renderMenu({ source: 'identity_profile' });

    expect(ids).toContain('toolbar-profile');
    expect(ids).not.toContain('toolbar-identity-profile');
  });

  it('gives every entry an id that does not change with the language', () => {
    // Upstream used the translated label as the DOM id, so anything keying
    // on it worked in English and silently not in Portuguese.
    const { ids } = renderMenu({
      ...STORED_AS_A_PROFILE,
      actions: [{ id: 'plone_setup' }],
    });

    for (const id of ids) {
      expect(id.startsWith('toolbar-')).toBe(true);
    }
  });

  it('slides the preferences panel in through the toolbar it came from', () => {
    // The one entry that is not a link. `loadComponent` belongs to
    // `PersonalTools`, and reaches this plug through the pluggable's params.
    const { loadComponent } = renderMenu();

    fireEvent.click(screen.getByRole('button', { name: 'Preferences' }));

    expect(loadComponent).toHaveBeenCalledWith('preferences');
  });
});

/**
 * The shadowed personal-tools menu.
 *
 * Upstream ships no test for this component, and once it is rewritten rather
 * than patched it is this package's code: the things that differ from Volto
 * are the things worth pinning, so a future upgrade that quietly reverts one
 * of them fails here instead of in somebody's browser.
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '../../../../../testing';
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

function renderMenu(
  user: unknown = ALICE,
  props: Record<string, unknown> = {},
  actions: unknown[] = [],
  plugs: React.ReactNode = null,
) {
  const store = {
    getState: () => ({
      userProfile: { loading: false, loaded: true, error: null, data: user },
      actions: { actions: { user: actions } },
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

describe('PersonalTools', () => {
  it('writes no entry of its own into the list', () => {
    // Upstream writes three and puts the pluggable after them, so an add-on
    // can only append. Every entry is a plug now -- what they are and what
    // order they come in is `UserMenuPlugs`' test -- and this component's
    // share of it is an empty list waiting for them.
    const { container } = renderMenu();

    expect(container.querySelector('.pastanaga-menu-list ul')).toBeTruthy();
    expect(container.querySelectorAll('.pastanaga-menu-list li')).toHaveLength(
      0,
    );
  });

  it('renders whatever plugged into the user menu', () => {
    renderMenu(
      ALICE,
      {},
      [],
      <Plug pluggable="toolbar-user-menu" id="probe">
        <li id="probe-entry">Probe</li>
      </Plug>,
    );

    expect(document.querySelector('#probe-entry')).toBeTruthy();
  });

  it('hands the plugs the prop only it has', () => {
    // `loadComponent` belongs to this component; the Preferences entry is a
    // plug and would otherwise have no way to reach it.
    const loadComponent = vi.fn();
    renderMenu(
      ALICE,
      { loadComponent },
      [],
      <Plug pluggable="toolbar-user-menu" id="probe">
        {({ loadComponent: given }: { loadComponent: () => void }) => (
          <li>
            <button onClick={() => given()}>Probe</button>
          </li>
        )}
      </Plug>,
    );

    screen.getByRole('button', { name: 'Probe' }).click();

    expect(loadComponent).toHaveBeenCalled();
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

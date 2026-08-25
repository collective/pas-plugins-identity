import { describe, expect, it } from 'vitest';
import { render, screen } from '../../testing';
import { MemoryRouter } from 'react-router-dom';
import React from 'react';

import {
  Pluggable,
  PluggablesProvider,
} from '@plone/volto/components/manage/Pluggable';
import IdentitiesMenuItem from './IdentitiesMenuItem';
import install from '../../config/menu';
import { IDENTITIES_PATH } from '../../config/routes';

/**
 * Render the plug the way Volto's user menu does: inside a provider, with the
 * matching `Pluggable` standing in for the one at the end of `PersonalTools`'
 * list. Rendering the plug on its own would prove nothing -- a `Plug` returns
 * null and registers a renderer, so the assertion has to come from the
 * pluggable that consumes it.
 */
function renderInMenu() {
  render(
    <MemoryRouter>
      <PluggablesProvider>
        <IdentitiesMenuItem />
        <ul>
          <Pluggable name="toolbar-user-menu" />
        </ul>
      </PluggablesProvider>
    </MemoryRouter>,
  );
}

describe('IdentitiesMenuItem', () => {
  it('renders a link into the identities view', () => {
    renderInMenu();

    const link = screen.getByRole('link', { name: /sign-in methods/i });

    expect(link.getAttribute('href')).toBe(IDENTITIES_PATH);
  });

  it('renders as a list item, because it lands inside the menu list', () => {
    renderInMenu();

    expect(screen.getByRole('listitem').tagName).toBe('LI');
  });

  it('renders nothing without a pluggable to land in', () => {
    render(
      <MemoryRouter>
        <PluggablesProvider>
          <IdentitiesMenuItem />
        </PluggablesProvider>
      </MemoryRouter>,
    );

    expect(screen.queryByRole('link')).toBeNull();
  });
});

describe('the menu install step', () => {
  it('registers the plug so it is mounted on every path', () => {
    const config = { settings: { appExtras: [] } } as any;

    install(config);

    const entry = config.settings.appExtras.find(
      (e: any) => e.component === IdentitiesMenuItem,
    );
    expect(entry).toBeTruthy();
    // Volto hands `match` to `matchPath`, and an empty path matches every
    // route -- which is what makes the plug reachable wherever the user
    // menu is opened.
    expect(entry.match).toBe('');
  });

  it('registers everything the menu needs on every path', () => {
    const config = { settings: { appExtras: [] } } as any;

    install(config);

    // The loader, plus one per menu entry -- including the three Volto used
    // to write into the list itself. The loader renders nothing: the entries
    // beside it read the user it puts in the store.
    expect(config.settings.appExtras).toHaveLength(7);
    expect(config.settings.appExtras.every((e: any) => e.match === '')).toBe(
      true,
    );
  });

  it('keeps whatever another add-on already registered', () => {
    const other = () => null;
    const config = {
      settings: { appExtras: [{ match: '', component: other, props: {} }] },
    } as any;

    install(config);

    expect(config.settings.appExtras).toHaveLength(8);
    expect(config.settings.appExtras[0].component).toBe(other);
  });
});

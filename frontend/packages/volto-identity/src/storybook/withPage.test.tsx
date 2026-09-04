import { afterEach, describe, expect, it } from 'vitest';
import { render } from '../testing';
import { MemoryRouter } from 'react-router-dom';
import { CookiesProvider } from 'react-cookie';
import { Provider } from 'react-redux';
import React from 'react';

import { ensureToolbarHost, PAGE_WIDTH } from './withPage';
import { VOLTO_CHROME } from '../stories/fixtures';
import Identities from '../components/Identities/Identities';

/**
 * What the story environment has to be able to do.
 *
 * Five pages here portal Volto's `Toolbar` into `#toolbar` and are wrapped in
 * `withCookies`. Every other test of those pages stubs the toolbar out, which
 * is right for a unit test and means nothing here would notice the *stories*
 * being unrenderable -- which they were, for both reasons at once.
 *
 * So this renders one of them for real, through the same helper the decorator
 * uses and the same provider it supplies. It is a test of the story
 * environment, not of the page.
 */

const LOADED = { loading: false, loaded: true, error: null };

function storyState() {
  return {
    identities: { ...LOADED, data: [] },
    linkableProviders: { ...LOADED, data: [] },
    loginProviders: { ...LOADED, data: [] },
    myProfile: {
      ...LOADED,
      data: { profile: '/identity-profiles/erico', emails: [] },
    },
    identityLinking: {},
    identityUnlink: {},
    preferredEmail: {},
    ...VOLTO_CHROME,
  };
}

describe('the story page environment', () => {
  afterEach(() => {
    document.getElementById('toolbar')?.remove();
  });

  it('gives the toolbar somewhere to go', () => {
    ensureToolbarHost();

    expect(document.getElementById('toolbar')).toBeTruthy();
  });

  it('makes only one, however often it is asked', () => {
    ensureToolbarHost();
    ensureToolbarHost();

    expect(document.querySelectorAll('#toolbar')).toHaveLength(1);
  });

  it('renders a page that portals its toolbar', () => {
    // Without the host this threw "Target container is not a DOM element";
    // without the provider, "Cannot read properties of null (reading
    // 'getAll')" out of react-cookie. Both were the whole story failing to
    // render, and neither was visible from the page's own tests.
    ensureToolbarHost();
    const state = storyState();
    const store = {
      getState: () => state,
      dispatch: (action: unknown) => action,
      subscribe: () => () => {},
    };

    render(
      <CookiesProvider>
        <Provider store={store as never}>
          <MemoryRouter initialEntries={['/identities']}>
            <Identities />
          </MemoryRouter>
        </Provider>
      </CookiesProvider>,
    );

    expect(document.querySelector('#page-identities')).toBeTruthy();
  });

  it('has a measure to constrain a story to', () => {
    expect(PAGE_WIDTH).toMatch(/^\d+px$/);
  });
});

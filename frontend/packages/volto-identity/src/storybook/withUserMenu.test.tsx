import { afterEach, describe, expect, it } from 'vitest';
import { render } from '../testing';
import React from 'react';

import {
  withMenuList,
  withPersonalTools,
  withToolbar,
  withToolbarButton,
} from './withUserMenu';

/**
 * That the menu markup lands where its stylesheet can reach it.
 *
 * Every rule for `.pastanaga-menu`, `.pastanaga-menu-list` and `.toolbar` is
 * nested under `#toolbar` in Volto's `toolbar.less`, so the class names alone
 * style nothing. A story with the classes and no ancestor renders an
 * unstyled column of links and looks like a broken component -- which is what
 * these decorators exist to stop, and what nothing else here would notice.
 *
 * There must also be exactly one `#toolbar`: Volto's pages find it with
 * `getElementById` to portal their own toolbar into.
 */

/** A story, as Storybook hands one to a decorator. */
const story = () => <a href="/identities">Sign-in methods</a>;
const context = {} as never;

describe('the user-menu decorators', () => {
  afterEach(() => {
    document.getElementById('toolbar')?.remove();
  });

  it('puts the panel inside #toolbar', () => {
    render(<>{withPersonalTools(story, context)}</>);

    const panel = document.querySelector('.personal-tools.pastanaga-menu');
    expect(panel).toBeTruthy();
    expect(panel?.closest('#toolbar')).toBeTruthy();
  });

  it('puts the list where the panel styles it', () => {
    render(
      <>{withPersonalTools(() => withMenuList(story, context), context)}</>,
    );

    const entry = document.querySelector('#toolbar .pastanaga-menu-list ul a');
    expect(entry).toBeTruthy();
  });

  it('puts the avatar on the toolbar button, inside #toolbar', () => {
    render(<>{withToolbarButton(story, context)}</>);

    const button = document.querySelector('button#toolbar-personal.user');
    expect(button).toBeTruthy();
    expect(button?.closest('#toolbar .toolbar')).toBeTruthy();
  });

  it('gives a component that brings its own markup just the ancestor', () => {
    render(<>{withToolbar(story, context)}</>);

    expect(document.querySelector('#toolbar a')).toBeTruthy();
    expect(document.querySelector('#toolbar .pastanaga-menu')).toBeNull();
  });

  it('never makes a second #toolbar', () => {
    // A duplicate earlier in the document would shadow the host that pages
    // portal their toolbar into, and `getElementById` would hand them this.
    render(
      <>
        {withPersonalTools(story, context)}
        {withToolbarButton(story, context)}
      </>,
    );

    expect(document.querySelectorAll('#toolbar')).toHaveLength(1);
  });
});

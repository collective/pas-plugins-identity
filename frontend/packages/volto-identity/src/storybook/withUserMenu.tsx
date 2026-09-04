/**
 * The two places this add-on puts something in Volto's toolbar.
 *
 * Both are markup the components land *inside* rather than markup they
 * render, and the whole of Volto's toolbar stylesheet is nested under an id:
 *
 * ```less
 * #toolbar {
 *   .toolbar { … }
 *   .pastanaga-menu { width: 100vw; height: calc(100vh - 100px); … }
 *   .pastanaga-menu-list { … }
 * }
 * ```
 *
 * So `#toolbar` is not decoration -- without that ancestor **none** of these
 * rules match, and a story showing the right class names still shows an
 * unstyled list. That is what made the menu stories look wrong, and it is why
 * `PersonalTools`, which renders `.personal-tools.pastanaga-menu` itself,
 * looked wrong even though it carries the markup already.
 *
 * There can be only one `#toolbar`: Volto's pages find it with
 * `getElementById` to portal their toolbar into, and a second one earlier in
 * the document would shadow it. So these decorators render *into* the one
 * `withPage` guarantees rather than making their own -- which is also what
 * happens on a real site, where the menu is a child of the toolbar it slides
 * over.
 *
 * The nesting, read out of `PersonalTools.jsx` and this package's
 * `Toolbar.jsx`:
 *
 * ```
 * <div id="toolbar">                              <- withToolbar
 *   <div class="personal-tools pastanaga-menu">   <- withPersonalTools
 *     <header class="header">…</header>
 *     <div class="pastanaga-menu-list">
 *       <ul>…entries…</ul>                        <- withMenuList
 *
 *   <div class="toolbar">                         <- withToolbarButton
 *     …<button class="user" id="toolbar-personal">…avatar…
 * ```
 * @module storybook/withUserMenu
 */
import React from 'react';
import { createPortal } from 'react-dom';
import type { Decorator } from '@storybook/react';
import { MemoryRouter } from 'react-router-dom';

import { ensureToolbarHost } from './withPage';

/**
 * Render children inside the one `#toolbar` there is.
 *
 * A portal rather than a wrapper element, so nothing has to invent a second
 * element with that id. What is rendered still belongs to the story's React
 * tree -- context, the router and the store all reach it -- and appears in
 * the preview's own document, so the canvas shows it.
 */
const InToolbar: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const host = ensureToolbarHost();
  return host ? createPortal(children, host) : null;
};

/**
 * The `#toolbar` ancestor every rule in `toolbar.less` is nested under.
 *
 * For a component that already renders its own toolbar markup -- the
 * shadowed `PersonalTools` is the whole of that -- and the base the two
 * decorators below build on.
 */
export const withToolbar: Decorator = (Story) => (
  <MemoryRouter>
    <InToolbar>
      <Story />
    </InToolbar>
  </MemoryRouter>
);

/**
 * The personal-tools panel, down to the list its entries sit in.
 *
 * Stops short of the `<ul>` because the plug stories have to put it inside
 * their `PluggablesProvider` -- a plug and the pluggable that consumes it
 * must share one provider, and the pluggable is what renders the entries.
 * `PluggablesProvider` contributes no DOM, so the nesting Volto's stylesheet
 * keys on comes out the same either way.
 */
export const withPersonalTools: Decorator = (Story) => (
  <MemoryRouter>
    <InToolbar>
      <div className="personal-tools pastanaga-menu">
        <div className="pastanaga-menu-list">
          <Story />
        </div>
      </div>
    </InToolbar>
  </MemoryRouter>
);

/**
 * The list itself, for a story that renders one entry rather than a plug.
 *
 * Compose it inside `withPersonalTools`: Storybook applies the first
 * decorator innermost, so `[withMenuList, withPersonalTools]` reads in the
 * order the DOM nests.
 */
export const withMenuList: Decorator = (Story) => (
  <ul>
    <Story />
  </ul>
);

/**
 * The toolbar button the avatar is drawn on.
 *
 * `#toolbar-personal` is the button this add-on's `Toolbar.jsx` replaces
 * Volto's camera icon in, so this is where the avatar is actually seen --
 * 30px, on the toolbar's own ground, rather than floating on the canvas.
 * `expanded` because the toolbar is 20px tall until it is.
 */
export const withToolbarButton: Decorator = (Story) => (
  <MemoryRouter>
    <InToolbar>
      <div className="toolbar expanded">
        <div className="toolbar-body">
          <div className="toolbar-actions">
            <div className="toolbar-bottom">
              <button className="user" id="toolbar-personal" type="button">
                <Story />
              </button>
            </div>
          </div>
        </div>
      </div>
    </InToolbar>
  </MemoryRouter>
);

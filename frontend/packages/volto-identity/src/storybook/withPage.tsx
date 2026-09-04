/**
 * The page context a story does not otherwise get.
 *
 * Modelled on `volto-light-theme`'s `withTheme`: one global decorator that
 * puts every story in the surroundings its component has on a real page,
 * rather than each story reinventing them. Three things a bare story lacks.
 *
 * 1. **Somewhere for the toolbar to go.** Five pages here portal Volto's
 *    `Toolbar` into `#toolbar`, an element Volto's app shell renders and
 *    Storybook does not. `createPortal` is called during render and throws on
 *    a null container, so those stories did not render at all -- which is what
 *    "the Identities story is broken" was.
 *
 * 2. **A cookie provider.** Volto's `Toolbar` is wrapped in `withCookies`, and
 *    without a provider above it `react-cookie` throws reading a jar that is
 *    not there. `start-client.jsx` wraps the whole app in one, so this is the
 *    real shell rather than a prop for the stories' benefit.
 *
 * 3. **A measure.** On the canvas a story stretches to the viewport, so a
 *    panel meant to be read at a page's width was seen at twice it. This
 *    constrains and centres, the way the theme's decorator does.
 *
 * A story that is genuinely full-bleed -- or that supplies its own container,
 * as everything inside `LoginPanel` does -- opts out with
 * `parameters: { fullBleed: true }`.
 * @module storybook/withPage
 */
import React from 'react';
import type { Decorator } from '@storybook/react';
import { CookiesProvider } from 'react-cookie';

/**
 * The width these pages are read at.
 *
 * Deliberately not a restatement of Semantic UI's container width: that is
 * computed from breakpoints and gutters rather than written down as a number,
 * so quoting one here would be an invention that looked like a fact. The
 * pages that use a `Container` still constrain themselves inside this; what
 * this is for is the panels and lists that do not, which were edge-to-edge.
 */
export const PAGE_WIDTH = '1000px';

/**
 * Make sure `#toolbar` exists before any story renders into it.
 *
 * At module scope rather than in an effect: `createPortal` reads the element
 * during the story's *render*, which happens before any effect of a decorator
 * above it has run. Appended to `document.body`, which is where Volto's app
 * shell puts it and what its fixed positioning expects.
 *
 * There can only be one, because Volto's toolbar finds it by
 * `getElementById`. `withUserMenu` therefore renders *into* this element
 * rather than making a second one -- the menu styles need `#toolbar` as an
 * ancestor, and a duplicate id would shadow this for the pages that portal
 * their toolbar here.
 *
 * @returns The host, or null where there is no document.
 */
export function ensureToolbarHost(): HTMLElement | null {
  if (typeof document === 'undefined') {
    return null;
  }
  const existing = document.getElementById('toolbar');
  if (existing) {
    return existing;
  }
  const host = document.createElement('div');
  host.id = 'toolbar';
  document.body.appendChild(host);
  return host;
}

ensureToolbarHost();

/**
 * Constrain and centre a story, unless it brings its own container.
 *
 * @param fullBleed Whether the story fills whatever it is given.
 * @param children The story.
 * @returns The wrapper, or the story unchanged.
 */
const PageShell: React.FC<{
  fullBleed: boolean;
  children: React.ReactNode;
}> = ({ fullBleed, children }) => {
  if (fullBleed) {
    return <>{children}</>;
  }
  return (
    <div
      style={{
        maxWidth: PAGE_WIDTH,
        padding: '1rem',
        margin: '0 auto',
      }}
    >
      {children}
    </div>
  );
};

export const withPage: Decorator = (Story, context) => (
  <CookiesProvider>
    <PageShell fullBleed={Boolean(context.parameters?.fullBleed)}>
      <Story />
    </PageShell>
  </CookiesProvider>
);

export default withPage;

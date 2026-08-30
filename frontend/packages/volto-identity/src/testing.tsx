/**
 * Test-only rendering.
 *
 * Every component in this package formats its strings through `react-intl`,
 * which means every one of them needs an `IntlProvider` somewhere above it or
 * it throws on the first render. Storybook's preview supplies one; this is its
 * counterpart for the tests, so no test file has to know that.
 *
 * Testing Library is re-exported so a test file still has a single import.
 * @module testing
 */
import React from 'react';
import type { ReactElement, ReactNode } from 'react';
import { createIntl, IntlProvider as BareIntlProvider } from 'react-intl';
import { MemoryRouter } from 'react-router-dom';
import {
  render as renderBare,
  type RenderOptions,
  type RenderResult,
} from '@testing-library/react';

/**
 * No message catalogue on purpose.
 *
 * The tests assert on what a reader sees, which for a locale with nothing
 * translated is each descriptor's `defaultMessage` -- exactly the English the
 * components used to hard-code. `onError` is silenced because "no message for
 * this id" is the expected state here, not a failure.
 */
/**
 * `react-intl` 3.12's provider, given its children back.
 *
 * The version Volto pins types `IntlProvider` as a class component whose
 * props never mention `children` -- React 17's types supplied that
 * implicitly and React 18's do not, so every use of it is a type error and
 * none of them is a bug. The cast restores the prop the component has always
 * accepted and changes nothing at runtime. Exported because the tests that
 * bring their own provider need the same repair.
 */
export const IntlProvider = BareIntlProvider as React.ComponentType<
  React.ComponentProps<typeof BareIntlProvider> & { children?: ReactNode }
>;

const WithIntl = ({ children }: { children: ReactNode }) => (
  <IntlProvider locale="en" defaultLocale="en" messages={{}} onError={() => {}}>
    {/* A router as well, for the same reason: components in this package
        link with `<Link>` rather than throwing the application away with a
        plain anchor, and `<Link>` outside a Router throws on first render.
        A test that needs to *observe* navigation still brings its own
        `MemoryRouter` and asserts on its location. */}
    <MemoryRouter>{children}</MemoryRouter>
  </IntlProvider>
);

/**
 * Render as Testing Library does, inside an `IntlProvider`.
 *
 * @param ui The element under test.
 * @param options Testing Library's own options.
 * @returns Whatever `@testing-library/react`'s `render` returns.
 */
export function render(
  ui: ReactElement,
  options?: RenderOptions,
): RenderResult {
  return renderBare(ui, { wrapper: WithIntl, ...options });
}

/**
 * An `IntlShape` for code that formats messages outside a component.
 *
 * The schema helpers build form labels in plain modules, so they take an
 * `intl` rather than calling `useIntl`. Tests need one without rendering
 * anything, and `createIntl` is how `react-intl` provides it.
 *
 * English with no catalogue, exactly as `WithIntl` renders: every message
 * falls back to its `defaultMessage`, which is what the assertions read.
 */
export const testIntl = createIntl({
  locale: 'en',
  defaultLocale: 'en',
  messages: {},
  onError: () => {},
});

export * from '@testing-library/react';

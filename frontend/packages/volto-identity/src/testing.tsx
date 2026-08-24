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
import { IntlProvider } from 'react-intl';
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
const WithIntl = ({ children }: { children: ReactNode }) => (
  <IntlProvider locale="en" defaultLocale="en" messages={{}} onError={() => {}}>
    {children}
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

export * from '@testing-library/react';

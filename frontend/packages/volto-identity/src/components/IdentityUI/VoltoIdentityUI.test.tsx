import { describe, expect, it } from 'vitest';
import React from 'react';
import { MemoryRouter, Route } from 'react-router-dom';
import { PasswordForm } from '@plone-collective/identity-core';

import { fireEvent, IntlProvider, render, screen } from '../../testing';
import VoltoIdentityUI from './VoltoIdentityUI';

function renderForm(messages: Record<string, string> = {}) {
  return render(<PasswordForm loading={false} onSubmit={() => {}} />, {
    wrapper: ({ children }) => (
      <IntlProvider locale="de" messages={messages} onError={() => {}}>
        <MemoryRouter>
          <VoltoIdentityUI>{children}</VoltoIdentityUI>
          <Route path="/passwordreset">
            <p>The password reset page</p>
          </Route>
        </MemoryRouter>
      </IntlProvider>
    ),
  });
}

describe('VoltoIdentityUI', () => {
  it("translates through Volto's catalogue", () => {
    renderForm({ Password: 'Passwort' });

    expect(screen.getByLabelText('Passwort')).toBeTruthy();
  });

  it('falls back to English where the catalogue has no translation', () => {
    renderForm({ Password: 'Passwort' });

    expect(screen.getByLabelText('Login name')).toBeTruthy();
  });

  it("links through Volto's router", () => {
    renderForm();

    // A plain anchor would ask the browser for a new page, which jsdom does
    // not do; only the router's link gets the reset page drawn.
    fireEvent.click(screen.getByText('Forgot your password?'));

    expect(screen.getByText('The password reset page')).toBeTruthy();
  });

  it("draws Volto's icons", () => {
    const { container } = renderForm();

    // Volto's `Icon` inlines the SVG file it was given, under the class it
    // was given. The core fallback is a stroked path of its own, which is
    // how it can be told apart.
    const icons = container.querySelectorAll('button svg.circled');
    expect(icons).toHaveLength(2);
    icons.forEach((icon) => expect(icon.getAttribute('stroke')).toBeNull());
  });
});

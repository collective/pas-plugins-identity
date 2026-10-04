import { describe, expect, it } from 'vitest';
import React from 'react';
import { render } from '../../testing';

import { IdentityUIProvider, useIdentityUI } from './IdentityUI';
import PasswordForm from '../Login/PasswordForm';

/** Print the paths the components below would link to. */
function Paths() {
  const { paths } = useIdentityUI();
  return <output>{paths.passwordReset}</output>;
}

describe('IdentityUIProvider', () => {
  it("links to Volto's pages when a frontend names none", () => {
    render(<Paths />);

    expect(document.querySelector('output')?.textContent).toBe(
      '/passwordreset',
    );
  });

  it("links to the frontend's own pages when it names them", () => {
    render(
      <IdentityUIProvider paths={{ passwordReset: '/reset-password' }}>
        <Paths />
      </IdentityUIProvider>,
    );

    expect(document.querySelector('output')?.textContent).toBe(
      '/reset-password',
    );
  });

  it("sends the password form's reset link there", () => {
    render(
      <IdentityUIProvider paths={{ passwordReset: '/reset-password' }}>
        <PasswordForm loading={false} onSubmit={() => {}} />
      </IdentityUIProvider>,
    );

    expect(
      document.querySelector('a[href="/reset-password"]')?.textContent,
    ).toBe('Forgot your password?');
  });
});

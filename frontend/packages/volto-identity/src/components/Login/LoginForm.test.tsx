import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '../../testing';
import { MemoryRouter } from 'react-router-dom';
import React from 'react';

import LoginForm from './LoginForm';
import type { LoginProvider } from '../../types';

const DEX: LoginProvider = {
  '@id': '/@login-providers/dex',
  id: 'dex',
  title: 'Dex',
  driver: 'oidc-generic',
};

const EMAIL: LoginProvider = {
  '@id': '/@login-providers/email',
  id: 'email',
  title: 'Email',
  driver: 'email',
};

function renderForm(
  props: Partial<React.ComponentProps<typeof LoginForm>> = {},
) {
  const onSelectProvider = vi.fn();
  const onSendMagicLink = vi.fn();
  const onPasswordLogin = vi.fn();
  const tree = (extra: Partial<React.ComponentProps<typeof LoginForm>>) => (
    // The password form links to /passwordreset, the way volto-authomatic's
    // does, so it needs a router.
    <MemoryRouter>
      <LoginForm
        providers={[DEX]}
        loading={false}
        starting={false}
        magicLinkSent={false}
        magicLinkLoading={false}
        passwordLoading={false}
        // The default here, not the product's: most of these are about the
        // picker, and a picker needs something to pick between.
        showPloneLogin
        onSelectProvider={onSelectProvider}
        onSendMagicLink={onSendMagicLink}
        onPasswordLogin={onPasswordLogin}
        {...props}
        {...extra}
      />
    </MemoryRouter>
  );
  const result = render(tree({}));
  return {
    onSelectProvider,
    onSendMagicLink,
    onPasswordLogin,
    // Re-render with the same component instance, so state a click put there
    // -- which provider was chosen -- survives the container answering.
    update: (extra: Partial<React.ComponentProps<typeof LoginForm>>) =>
      result.rerender(tree(extra)),
  };
}

/**
 * Reach the magic-link form the way a visitor does, from the picker.
 *
 * Only needed where the picker is on screen: with email as the single way
 * in, the form is the page and there is no button to press.
 */
function openEmail() {
  fireEvent.click(screen.getByText('Email'));
}

describe('LoginForm', () => {
  it('renders a button per provider', () => {
    renderForm({ providers: [DEX, { ...DEX, id: 'github', title: 'GitHub' }] });

    // Three buttons, not two: the local password is offered as one of these
    // as well, so the list carries one more than there are providers.
    const list = document.querySelector('.identity-providers');
    expect(list?.querySelectorAll('button')).toHaveLength(3);
    expect(screen.getByText('Dex')).toBeTruthy();
  });

  it('reports the chosen provider', () => {
    const { onSelectProvider } = renderForm();

    fireEvent.click(screen.getByText('Dex'));

    expect(onSelectProvider).toHaveBeenCalledWith(DEX);
  });

  it('disables the buttons once a redirect is under way', () => {
    renderForm({ starting: true });

    // Otherwise an impatient second click starts a second flow, whose state
    // replaces the first one's and strands the redirect already in flight.
    expect(screen.getByText('Dex').closest('button')?.disabled).toBe(true);
  });

  it('says so while the options are loading', () => {
    renderForm({ loading: true });

    expect(screen.getByRole('status').textContent).toContain('Loading');
  });

  it('draws the wait as well as describing it', () => {
    renderForm({ loading: true });

    // Decorative: the text beside it is what a screen reader reads, which is
    // why the spinner is hidden from one rather than labelled twice.
    const overlay = document.querySelector('.identity-overlay--waiting');
    expect(overlay).toBeTruthy();
    const spinner = overlay?.querySelector('.identity-spinner');
    expect(spinner).toBeTruthy();
    expect(spinner?.getAttribute('aria-hidden')).toBe('true');
  });

  it('draws the redirect the same way', () => {
    // It is the same kind of wait -- something happening this page cannot
    // show -- and used to be the one state rendered as bare body text.
    renderForm({ showPloneLogin: false, providers: [DEX] });

    const overlay = document.querySelector('.identity-overlay--waiting');
    expect(overlay).toBeTruthy();
    expect(overlay?.querySelector('.identity-spinner')).toBeTruthy();
    expect(overlay?.textContent).toContain('Dex');
  });

  it('says where it is going while the options stay put', () => {
    // Greying the buttons says they cannot be pressed, not that anything is
    // happening or where it is going. Both used to be true only on the
    // single-provider page.
    renderForm({ providers: [DEX, EMAIL] });
    fireEvent.click(screen.getByText('Dex'));

    // `starting` is the container's answer, so it is passed rather than
    // observed -- what this pins is that the picker is still underneath.
    expect(document.querySelector('.identity-providers')).toBeTruthy();
  });

  it('names the provider it is redirecting to', () => {
    const { update } = renderForm({ providers: [DEX, EMAIL] });
    fireEvent.click(screen.getByText('Dex'));
    update({ starting: true });

    const overlay = document.querySelector('.identity-overlay--waiting');
    expect(overlay?.textContent).toContain('Dex');
    expect(document.querySelector('.identity-providers')).toBeTruthy();
  });

  it('lets a refusal be dismissed so the options can be used again', () => {
    // Left up, it covers the buttons the reader would press to try again.
    renderForm({ error: { status: 502 } });

    expect(screen.getByRole('alert')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));

    expect(document.querySelector('.identity-overlay--error')).toBeNull();
    expect(screen.getByText('Dex')).toBeTruthy();
  });

  it('is just the password form on a site with no providers', () => {
    // This page replaces Volto's login, so hiding the password here left a
    // site with local accounts and no provider -- an authorization server,
    // for instance -- with no way in at all. With nothing to choose between,
    // the disclosure is one click between the visitor and the only form
    // there is, so the fields are on screen straight away.
    renderForm({ providers: [] });

    expect(screen.queryByText('Sign in with a password')).toBeNull();
    expect(screen.getByLabelText('Login name')).toBeTruthy();
    expect(screen.getByLabelText('Password')).toBeTruthy();
  });

  it('does not announce the absence of providers', () => {
    // The panel's description already says the account is one on this site;
    // saying "none are configured" on top of that reads as an error over a
    // form that works.
    renderForm({ providers: [] });

    expect(screen.queryByText(/No sign-in providers/)).toBeNull();
  });

  it('offers the password as one of the buttons, not a line of text', () => {
    renderForm();

    // The label is a span inside the button now, so that an operator's icon
    // can sit beside it.
    const button = screen
      .getByText('Sign in with a password')
      .closest('button') as HTMLButtonElement;
    expect(button.closest('.identity-providers')).toBeTruthy();
    // volto-authomatic's `plone` colours, so the same button is the same
    // blue in both add-ons.
    expect(button.className).toContain('identity-provider--plone');
    expect(screen.queryByLabelText('Login name')).toBeNull();
  });

  it('replaces the providers with the password form, not adds to it', () => {
    // The password is a different way to sign in, not an extra field on the
    // provider list; leaving the buttons above it made the page read as one
    // form with a stray row of buttons on top.
    renderForm({ providers: [DEX, EMAIL] });

    fireEvent.click(screen.getByText('Sign in with a password'));

    expect(document.querySelector('.identity-providers')).toBeNull();
    expect(screen.queryByLabelText('Email address')).toBeNull();
    expect(screen.getByLabelText('Login name')).toBeTruthy();
  });

  it('offers a way back to them', () => {
    // Hiding the providers with no way back strands anybody who opened the
    // password form by mistake on the one form they cannot use.
    renderForm({ providers: [DEX, EMAIL] });
    fireEvent.click(screen.getByText('Sign in with a password'));

    fireEvent.click(screen.getByText('Back to sign-in options'));

    expect(screen.getByText('Dex')).toBeTruthy();
    expect(screen.getByText('Email')).toBeTruthy();
    expect(screen.queryByLabelText('Login name')).toBeNull();
  });

  it('offers a way back out of the email form too', () => {
    // The same escape, from the step that replaced the inline form.
    renderForm({ providers: [DEX, EMAIL] });
    fireEvent.click(screen.getByText('Email'));

    fireEvent.click(screen.getByText('Back to sign-in options'));

    expect(screen.getByText('Dex')).toBeTruthy();
    expect(screen.queryByLabelText('Email address')).toBeNull();
  });

  it('offers a password alongside the providers', () => {
    renderForm();

    expect(screen.getByText('Sign in with a password')).toBeTruthy();
  });

  it('submits the credentials that were typed', () => {
    const { onPasswordLogin } = renderForm();
    fireEvent.click(screen.getByText('Sign in with a password'));

    fireEvent.change(screen.getByLabelText('Login name'), {
      target: { value: 'alice' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'hunter2' },
    });
    // An icon button since the form took volto-authomatic's shape, so it is
    // found by its accessible name rather than its text.
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(onPasswordLogin).toHaveBeenCalledWith('alice', 'hunter2');
  });

  it('does not distinguish a wrong name from a wrong password', () => {
    // Telling them apart is an account-enumeration oracle.
    renderForm({ passwordError: { status: 401 } });
    fireEvent.click(screen.getByText('Sign in with a password'));

    expect(screen.getByRole('alert').textContent).toContain('did not match');
  });

  it('reports a failed start', () => {
    renderForm({ error: { status: 502 } });

    expect(screen.getByRole('alert').textContent).toContain('not available');
  });

  it('offers no password button when the site turned it off', () => {
    renderForm({ showPloneLogin: false, providers: [DEX, EMAIL] });

    expect(screen.queryByText('Sign in with a password')).toBeNull();
    expect(screen.getByText('Dex')).toBeTruthy();
  });

  it('still offers the password when nothing else is configured', () => {
    // The setting decides whether a password sits *beside* the providers. A
    // fresh install has the add-on on and no provider yet, and must not be a
    // site with no way in at all.
    renderForm({ showPloneLogin: false, providers: [] });

    expect(screen.getByLabelText(/Login Name/i)).toBeTruthy();
  });

  it('goes straight to the only provider there is', () => {
    // One button asking somebody to confirm the only thing that can happen
    // is a click that carries no decision.
    const { onSelectProvider } = renderForm({
      showPloneLogin: false,
      providers: [DEX],
    });

    expect(onSelectProvider).toHaveBeenCalledWith(DEX);
  });

  it('says where it is taking them rather than flashing a button', () => {
    renderForm({ showPloneLogin: false, providers: [DEX] });

    expect(screen.getByRole('status').textContent).toContain('Dex');
  });

  it('does not redirect when there is a choice to make', () => {
    const { onSelectProvider } = renderForm({
      showPloneLogin: false,
      providers: [DEX, { ...DEX, id: 'github', title: 'GitHub' }],
    });

    expect(onSelectProvider).not.toHaveBeenCalled();
  });

  it('does not redirect past a provider that just failed', () => {
    // Otherwise an unreachable provider is an unbreakable loop: start, fail,
    // render, start again.
    const { onSelectProvider } = renderForm({
      showPloneLogin: false,
      providers: [DEX],
      error: new Error('nope'),
    });

    expect(onSelectProvider).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toBeTruthy();
  });

  it('is just the magic-link form when that is the only way in', () => {
    renderForm({ showPloneLogin: false, providers: [EMAIL] });

    expect(screen.queryByText('Sign in with a password')).toBeNull();
    expect(document.querySelector('.identity-providers')).toBeNull();
  });

  it('offers the email provider as a button, not an open field', () => {
    renderForm({ providers: [DEX, EMAIL] });

    // It was the one way in that did not look like one: a labelled input
    // standing open under a page asking which method to use.
    const list = document.querySelector('.identity-providers');
    expect(list?.textContent).toContain('Email');
    expect(screen.queryByLabelText('Email address')).toBeNull();
  });

  it('opens the email field on the next step', () => {
    renderForm({ providers: [DEX, EMAIL] });

    fireEvent.click(screen.getByText('Email'));

    // The same second step the password button already had: the picker is
    // replaced rather than added to.
    expect(document.querySelector('.identity-providers')).toBeNull();
    expect(screen.getByLabelText('Email address')).toBeTruthy();
  });

  it('does not redirect when the email button is pressed', () => {
    // It answers with a message rather than an authorize URL, so treating it
    // like the others would start a flow that cannot finish.
    const { onSelectProvider } = renderForm({ providers: [DEX, EMAIL] });

    fireEvent.click(screen.getByText('Email'));

    expect(onSelectProvider).not.toHaveBeenCalled();
  });

  it('closes the password form when the email one opens', () => {
    // One disclosure, not one boolean each: two open forms is not a state
    // this page has.
    renderForm({ providers: [DEX, EMAIL] });
    fireEvent.click(screen.getByText('Sign in with a password'));
    fireEvent.click(screen.getByText('Back to sign-in options'));

    fireEvent.click(screen.getByText('Email'));

    expect(screen.queryByLabelText('Login name')).toBeNull();
    expect(screen.getByLabelText('Email address')).toBeTruthy();
  });

  it('offers no magic-link form when no email provider is configured', () => {
    renderForm({ providers: [DEX] });

    expect(screen.queryByLabelText('Email address')).toBeNull();
  });
});

describe('MagicLinkForm', () => {
  it('sends the address typed in', () => {
    const { onSendMagicLink } = renderForm({ providers: [EMAIL] });
    openEmail();

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: 'erico@plone.org' },
    });
    // An icon button since the form took the password form's shape, so it
    // is found by its accessible name rather than its text.
    fireEvent.click(screen.getByRole('button', { name: 'Email me a link' }));

    expect(onSendMagicLink).toHaveBeenCalledWith('erico@plone.org');
  });

  it('will not send an empty address', () => {
    const { onSendMagicLink } = renderForm({ providers: [EMAIL] });
    openEmail();

    // An icon button since the form took the password form's shape, so it
    // is found by its accessible name rather than its text.
    fireEvent.click(screen.getByRole('button', { name: 'Email me a link' }));

    expect(onSendMagicLink).not.toHaveBeenCalled();
  });

  it('trims what was typed', () => {
    const { onSendMagicLink } = renderForm({ providers: [EMAIL] });
    openEmail();

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: '  erico@plone.org  ' },
    });
    // An icon button since the form took the password form's shape, so it
    // is found by its accessible name rather than its text.
    fireEvent.click(screen.getByRole('button', { name: 'Email me a link' }));

    expect(onSendMagicLink).toHaveBeenCalledWith('erico@plone.org');
  });

  it('does not say whether the address is known', () => {
    renderForm({ providers: [EMAIL], magicLinkSent: true });
    openEmail();

    // The backend answers identically for known and unknown addresses; a UI
    // that distinguished them would undo that.
    const message = screen.getByRole('status').textContent ?? '';
    expect(message).toContain('If that address');
    expect(screen.queryByLabelText('Email address')).toBeNull();
  });
});

describe('MagicLinkForm shape', () => {
  it('is the same form the password one is', () => {
    // A bare label and input beside a fully dressed PloneAuth, on the same
    // card, one click apart: the two forms on this page ask for one and two
    // fields and are otherwise the same form.
    renderForm({ providers: [DEX, EMAIL] });
    openEmail();

    const form = document.querySelector('form.PloneAuth.identity-magic-link');
    expect(form).toBeTruthy();
    expect(form?.querySelector('.form .react-aria-TextField')).toBeTruthy();
    expect(
      form?.querySelector('.actions #magic-link-form-submit'),
    ).toBeTruthy();
  });
});

describe('PasswordForm shape', () => {
  it('uses the same markup the standard Volto login form does', () => {
    // The classes are volto-authomatic's, and the styles are ported from it:
    // two add-ons that both replace /login looking like two different
    // products is worse than either looking like itself.
    renderForm();
    fireEvent.click(screen.getByText('Sign in with a password'));

    expect(document.querySelector('form.PloneAuth')).toBeTruthy();
    expect(document.querySelector('.PloneAuth .actions')).toBeTruthy();
    expect(document.querySelector('#login-form-submit')).toBeTruthy();
    expect(document.querySelector('#login-form-cancel')).toBeTruthy();
  });

  it('clears what was typed rather than submitting it', () => {
    const { onPasswordLogin } = renderForm();
    fireEvent.click(screen.getByText('Sign in with a password'));
    fireEvent.change(screen.getByLabelText('Login name'), {
      target: { value: 'alice' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Clear' }));

    expect(
      (screen.getByLabelText('Login name') as HTMLInputElement).value,
    ).toBe('');
    expect(onPasswordLogin).not.toHaveBeenCalled();
  });
});

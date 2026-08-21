import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
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
  render(
    <LoginForm
      providers={[DEX]}
      loading={false}
      starting={false}
      magicLinkSent={false}
      magicLinkLoading={false}
      onSelectProvider={onSelectProvider}
      onSendMagicLink={onSendMagicLink}
      {...props}
    />,
  );
  return { onSelectProvider, onSendMagicLink };
}

describe('LoginForm', () => {
  it('renders a button per provider', () => {
    renderForm({ providers: [DEX, { ...DEX, id: 'github', title: 'GitHub' }] });

    expect(screen.getAllByRole('button')).toHaveLength(2);
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

  it('says so when a site has none configured', () => {
    renderForm({ providers: [] });

    expect(screen.getByText(/No sign-in options/)).toBeTruthy();
    expect(screen.queryAllByRole('button')).toHaveLength(0);
  });

  it('reports a failed start', () => {
    renderForm({ error: { status: 502 } });

    expect(screen.getByRole('alert').textContent).toContain('not available');
  });

  it('keeps the email provider out of the button list', () => {
    renderForm({ providers: [DEX, EMAIL] });

    // The magic link is a form, not a redirect, so a button for it would do
    // the wrong thing.
    expect(screen.queryByText('Email')).toBeNull();
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

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: 'erico@plone.org' },
    });
    fireEvent.click(screen.getByText('Email me a link'));

    expect(onSendMagicLink).toHaveBeenCalledWith('erico@plone.org');
  });

  it('will not send an empty address', () => {
    const { onSendMagicLink } = renderForm({ providers: [EMAIL] });

    fireEvent.click(screen.getByText('Email me a link'));

    expect(onSendMagicLink).not.toHaveBeenCalled();
  });

  it('trims what was typed', () => {
    const { onSendMagicLink } = renderForm({ providers: [EMAIL] });

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: '  erico@plone.org  ' },
    });
    fireEvent.click(screen.getByText('Email me a link'));

    expect(onSendMagicLink).toHaveBeenCalledWith('erico@plone.org');
  });

  it('does not say whether the address is known', () => {
    renderForm({ providers: [EMAIL], magicLinkSent: true });

    // The backend answers identically for known and unknown addresses; a UI
    // that distinguished them would undo that.
    const message = screen.getByRole('status').textContent ?? '';
    expect(message).toContain('If that address');
    expect(screen.queryByLabelText('Email address')).toBeNull();
  });
});

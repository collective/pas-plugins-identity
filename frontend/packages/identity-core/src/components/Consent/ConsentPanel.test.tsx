import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '../../testing';
import React from 'react';

import ConsentPanel from './ConsentPanel';
import type { ConsentRequest } from '../../types';

const REQUEST: ConsentRequest = {
  '@id': 'http://id.example.org/@oauth-consent',
  client: { id: 'app', title: 'Example App' },
  user: { id: 'alice', label: 'Alice Liddell' },
  scopes: [
    { id: 'openid', claims: [] },
    { id: 'profile', claims: ['name', 'preferred_username'] },
    { id: 'email', claims: ['email', 'email_verified'] },
  ],
  authorize_url: 'http://id.example.org/@@oauth-authorize',
  params: { response_type: 'code', client_id: 'app' },
  authenticator: 'token',
};

function renderPanel(
  props: Partial<React.ComponentProps<typeof ConsentPanel>> = {},
) {
  const onAnswer = vi.fn();
  render(
    <ConsentPanel
      request={REQUEST}
      loading={false}
      answering={false}
      onAnswer={onAnswer}
      {...props}
    />,
  );
  return { onAnswer };
}

describe('ConsentPanel', () => {
  it('names the application doing the asking', () => {
    renderPanel();

    expect(screen.getByRole('heading').textContent).toContain('Example App');
  });

  it('says who would be agreeing', () => {
    // The browser may hold a session the user forgot about, and agreeing on
    // behalf of the wrong account is the mistake this screen exists to make
    // visible.
    renderPanel();

    expect(screen.getByText(/Alice Liddell/)).toBeTruthy();
  });

  it('lists what would actually be released, not the scope names', () => {
    // "profile" means nothing to the person being asked.
    renderPanel();

    expect(screen.getByText('preferred_username')).toBeTruthy();
    expect(screen.queryByText('profile')).toBeNull();
  });

  it('names each claim once however many scopes carry it', () => {
    renderPanel({
      request: {
        ...REQUEST,
        scopes: [
          { id: 'profile', claims: ['name'] },
          { id: 'other', claims: ['name'] },
        ],
      },
    });

    expect(screen.getAllByText('name')).toHaveLength(1);
  });

  it('says plainly when a request releases nothing', () => {
    // `openid` alone asks for an identity and gates no claim. An empty list
    // under "It will be able to read:" reads as a rendering failure.
    renderPanel({
      request: { ...REQUEST, scopes: [{ id: 'openid', claims: [] }] },
    });

    expect(screen.getByText(/nothing beyond the fact/)).toBeTruthy();
  });

  it('offers both answers', () => {
    renderPanel();

    expect(screen.getByRole('button', { name: 'Allow' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Deny' })).toBeTruthy();
  });

  it('reports agreement', () => {
    const { onAnswer } = renderPanel();

    fireEvent.click(screen.getByRole('button', { name: 'Allow' }));

    expect(onAnswer).toHaveBeenCalledWith(true);
  });

  it('reports refusal', () => {
    const { onAnswer } = renderPanel();

    fireEvent.click(screen.getByRole('button', { name: 'Deny' }));

    expect(onAnswer).toHaveBeenCalledWith(false);
  });

  it('takes no second answer once one is on its way', () => {
    renderPanel({ answering: true });

    expect(
      (screen.getByRole('button', { name: 'Allow' }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });

  it('says so while the request is loading', () => {
    renderPanel({ request: null, loading: true });

    expect(screen.getByRole('status').textContent).toContain('Loading');
  });

  it('waits rather than refusing before the first answer arrives', () => {
    // No request and no error yet is the first render, not a failure.
    renderPanel({ request: null, loading: false });

    expect(screen.getByRole('status')).toBeTruthy();
  });

  it('offers no answer to a request it could not describe', () => {
    // An "Allow" here would be agreeing to something the page cannot show.
    renderPanel({ request: null, error: new Error('nope') });

    expect(screen.getByRole('alert')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Allow' })).toBeNull();
  });
});

import { describe, expect, it, vi } from 'vitest';
import React from 'react';
import { fireEvent, render, screen } from '../../testing';

import ConfirmEmailCard from './ConfirmEmailCard';
import type { ConfirmEmailCardProps } from './ConfirmEmailCard';
import type { ProfileEmail } from '../../types';

const EMAILS: ProfileEmail[] = [
  { address: 'alice@example.com', verified: true, preferred: false },
  { address: 'alice@example.org', verified: true, preferred: true },
  { address: 'alice@example.net', verified: false, preferred: false },
];

function renderCard(props: Partial<ConfirmEmailCardProps> = {}) {
  const onConfirm = vi.fn();
  render(
    <ConfirmEmailCard
      status="asking"
      emails={EMAILS}
      busy={false}
      failed={false}
      onConfirm={onConfirm}
      {...props}
    />,
  );
  return onConfirm;
}

describe('ConfirmEmailCard', () => {
  it('offers only the verified addresses', () => {
    renderCard();

    expect(screen.getAllByRole('radio')).toHaveLength(2);
    expect(screen.queryByLabelText('alice@example.net')).toBeNull();
  });

  it('starts from the address already standing for the user', () => {
    renderCard();

    expect(
      (screen.getByLabelText('alice@example.org') as HTMLInputElement).checked,
    ).toBe(true);
  });

  it('confirms the address chosen', () => {
    const onConfirm = renderCard();

    fireEvent.click(screen.getByLabelText('alice@example.com'));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }));

    expect(onConfirm).toHaveBeenCalledWith('alice@example.com');
  });

  it('cannot be sent twice while the first answer is on its way', () => {
    renderCard({ busy: true });

    expect(
      (screen.getByRole('button', { name: 'Confirm' }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });

  it('says when the backend refused the answer', () => {
    renderCard({ failed: true });

    expect(screen.getByRole('alert').textContent).toMatch(/could not be/);
  });

  it('says which address it recorded, and leads on', () => {
    renderCard({ status: 'done', recorded: 'alice@example.com' });

    expect(screen.getByRole('status').textContent).toBe(
      'This site will use alice@example.com for you.',
    );
    expect(
      screen.getByText('Continue').closest('a')?.getAttribute('href'),
    ).toBe('/');
  });

  it('says when there is nothing to confirm', () => {
    renderCard({ status: 'nothing' });

    expect(screen.getByRole('status').textContent).toMatch(/no email address/);
    expect(screen.queryByRole('radio')).toBeNull();
  });

  it('says so while the profile is on its way', () => {
    renderCard({ status: 'loading' });

    expect(screen.getByRole('status').textContent).toBe('Loading…');
  });
});

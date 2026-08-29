import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '../../testing';
import React from 'react';

import ProfileEmails from './ProfileEmails';
import type { ProfileEmail } from '../../types';

const PREFERRED: ProfileEmail = {
  address: 'erico@plone.org',
  verified: true,
  preferred: true,
};

const OTHER: ProfileEmail = {
  address: 'erico@example.com',
  verified: false,
  preferred: false,
};

function renderPanel(
  props: Partial<React.ComponentProps<typeof ProfileEmails>> = {},
) {
  const onVerify = vi.fn();
  const onPrefer = vi.fn();
  render(
    <ProfileEmails
      emails={[PREFERRED, OTHER]}
      loading={false}
      busy={false}
      sent={false}
      onVerify={onVerify}
      onPrefer={onPrefer}
      {...props}
    />,
  );
  return { onVerify, onPrefer };
}

describe('ProfileEmails', () => {
  it('lists every address on the profile', () => {
    renderPanel();

    expect(screen.getByText('erico@plone.org')).toBeTruthy();
    expect(screen.getByText('erico@example.com')).toBeTruthy();
  });

  it('marks the one this site uses', () => {
    renderPanel();

    expect(screen.getByText('Preferred')).toBeTruthy();
  });

  describe('choosing which address stands for you', () => {
    it('offers it on every address but the one already chosen', () => {
      renderPanel();

      expect(
        screen.getAllByRole('button', { name: 'Make preferred' }),
      ).toHaveLength(1);
    });

    it('hands back the address that was picked', () => {
      const { onPrefer } = renderPanel();

      fireEvent.click(screen.getByRole('button', { name: 'Make preferred' }));

      expect(onPrefer).toHaveBeenCalledWith('erico@example.com');
    });

    it('is not offered at all without a handler', () => {
      // Rendered inert would be worse than never offered: a button that does
      // nothing when clicked reads as a broken page.
      renderPanel({ onPrefer: undefined });

      expect(
        screen.queryByRole('button', { name: 'Make preferred' }),
      ).toBeNull();
    });

    it('says nothing about ordering when there is one address', () => {
      renderPanel({ emails: [PREFERRED] });

      expect(
        screen.queryByRole('button', { name: 'Make preferred' }),
      ).toBeNull();
    });

    it('is held while something else is in flight', () => {
      renderPanel({ busy: true });

      expect(
        screen
          .getByRole('button', { name: 'Make preferred' })
          .hasAttribute('disabled'),
      ).toBe(true);
    });
  });

  it('offers a verification only for an address that has none', () => {
    renderPanel();

    expect(screen.getAllByRole('button', { name: 'Verify' })).toHaveLength(1);
  });
});

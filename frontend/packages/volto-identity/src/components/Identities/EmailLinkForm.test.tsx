import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '../../testing';
import React from 'react';

import EmailLinkForm from './EmailLinkForm';

function renderForm(
  props: Partial<React.ComponentProps<typeof EmailLinkForm>> = {},
) {
  const onSend = vi.fn();
  render(
    <EmailLinkForm sent={false} loading={false} onSend={onSend} {...props} />,
  );
  return { onSend };
}

describe('EmailLinkForm', () => {
  it('will not send an empty address', () => {
    const { onSend } = renderForm();

    expect(screen.getByRole('button')).toBeDisabled();
    expect(onSend).not.toHaveBeenCalled();
  });

  it('sends the address that was typed', () => {
    const { onSend } = renderForm();

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: 'erico@plone.org' },
    });
    fireEvent.click(screen.getByRole('button'));

    expect(onSend).toHaveBeenCalledWith('erico@plone.org');
  });

  it('trims what it sends', () => {
    const { onSend } = renderForm();

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: '  erico@plone.org  ' },
    });
    fireEvent.click(screen.getByRole('button'));

    expect(onSend).toHaveBeenCalledWith('erico@plone.org');
  });

  it('says the link has to be opened while still signed in', () => {
    // The one thing a user can get wrong that nothing else will tell them:
    // the confirmation is refused if it is completed by another session.
    renderForm({ sent: true });

    expect(screen.getByRole('status').textContent).toContain('signed in here');
  });

  it('offers no field once the mail is out', () => {
    renderForm({ sent: true });

    expect(screen.queryByLabelText('Email address')).toBeNull();
  });
});

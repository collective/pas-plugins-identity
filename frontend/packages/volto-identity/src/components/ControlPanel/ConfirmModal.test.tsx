import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render } from '../../testing';
import React from 'react';

import ConfirmModal from './ConfirmModal';

function renderModal(
  props: Partial<React.ComponentProps<typeof ConfirmModal>> = {},
) {
  const onCancel = vi.fn();
  const onConfirm = vi.fn();
  render(
    <ConfirmModal
      open
      header="GitHub"
      content="This cannot be undone."
      onCancel={onCancel}
      onConfirm={onConfirm}
      {...props}
    />,
  );
  return { onCancel, onConfirm };
}

/** The dialog is a portal, so it is mounted beside the render container. */
const action = (name: string) =>
  document.querySelector(`[data-action="${name}"]`)!;

describe('ConfirmModal', () => {
  it('says what is about to happen', () => {
    renderModal();

    expect(document.body.textContent).toContain('This cannot be undone.');
  });

  it('goes through with it on confirm', () => {
    const { onConfirm } = renderModal();

    fireEvent.click(action('confirm'));

    expect(onConfirm).toHaveBeenCalled();
  });

  it('does not on cancel', () => {
    const { onCancel, onConfirm } = renderModal();

    fireEvent.click(action('cancel'));

    expect(onCancel).toHaveBeenCalled();
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('lets the caller name the destructive action', () => {
    // "Delete" is wrong for withdrawing a grant, and a button that misnames
    // what it does is worse than no button.
    renderModal({ confirmLabel: 'Withdraw access' });

    expect(action('confirm').textContent).toBe('Withdraw access');
  });

  it('is not mounted when it is not being asked', () => {
    renderModal({ open: false });

    expect(document.querySelector('[data-action="confirm"]')).toBeNull();
  });
});

import { describe, expect, it, vi } from 'vitest';
import React from 'react';
import { fireEvent, render, screen } from '../../testing';

import ConfirmDialog from './ConfirmDialog';

function renderDialog(isOpen = true) {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  render(
    <ConfirmDialog
      isOpen={isOpen}
      title="Example App"
      message="Withdraw access for Example App?"
      confirmLabel="Withdraw access"
      onConfirm={onConfirm}
      onCancel={onCancel}
    />,
  );
  return { onConfirm, onCancel };
}

describe('ConfirmDialog', () => {
  it('asks, as a dialog that has to be answered', () => {
    renderDialog();

    const dialog = screen.getByRole('alertdialog');
    expect(dialog.textContent).toContain('Example App');
    expect(dialog.textContent).toContain('Withdraw access for Example App?');
  });

  it('goes ahead only from the button named for it', () => {
    const { onConfirm, onCancel } = renderDialog();

    fireEvent.click(screen.getByRole('button', { name: 'Withdraw access' }));

    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onCancel).not.toHaveBeenCalled();
  });

  it('can be turned down', () => {
    const { onConfirm, onCancel } = renderDialog();

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(onCancel).toHaveBeenCalledOnce();
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('shows nothing until it is asked', () => {
    renderDialog(false);

    expect(screen.queryByRole('alertdialog')).toBeNull();
  });
});

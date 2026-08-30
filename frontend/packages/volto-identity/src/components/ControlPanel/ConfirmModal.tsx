/**
 * Asking before something destructive, in the page rather than over it.
 *
 * Three panels used `window.confirm` — deleting a provider, deleting an OAuth
 * client, withdrawing a grant. It blocks the whole browser, it cannot be
 * styled, it reads as a different application than the panel around it, and a
 * test has to stub a global to reach the code behind it (Érico, 2026-08-29).
 * Volto's own answer is a modal; `ContentsDeleteModal` is the reference.
 *
 * One component for all three, because the question is always the same shape:
 * a heading, what is about to be lost, and two buttons where the destructive
 * one is the one that looks destructive.
 * @module components/ControlPanel/ConfirmModal
 */
import React from 'react';
import { Button, Confirm } from 'semantic-ui-react';
import { defineMessages, useIntl } from 'react-intl';

const messages = defineMessages({
  cancel: { id: 'Cancel', defaultMessage: 'Cancel' },
  confirm: { id: 'Delete', defaultMessage: 'Delete' },
});

interface ConfirmModalProps {
  /** Whether the question is being asked. */
  open: boolean;
  /** The heading, which names the thing rather than the action. */
  header: string;
  /** What is about to happen, and what cannot be undone about it. */
  content: string;
  /** Label for the destructive button; defaults to Delete. */
  confirmLabel?: string;
  onCancel: () => void;
  onConfirm: () => void;
}

const ConfirmModal: React.FC<ConfirmModalProps> = ({
  open,
  header,
  content,
  confirmLabel,
  onCancel,
  onConfirm,
}) => {
  const intl = useIntl();

  return (
    <Confirm
      open={open}
      header={header}
      content={content}
      cancelButton={
        <Button data-action="cancel">
          {intl.formatMessage(messages.cancel)}
        </Button>
      }
      confirmButton={
        <Button negative data-action="confirm">
          {confirmLabel ?? intl.formatMessage(messages.confirm)}
        </Button>
      }
      onCancel={onCancel}
      onConfirm={onConfirm}
    />
  );
};

export default ConfirmModal;

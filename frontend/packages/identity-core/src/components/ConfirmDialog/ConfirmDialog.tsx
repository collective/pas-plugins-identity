/**
 * Asking before something that cannot be taken back.
 *
 * React Aria's modal dialog, so focus is held inside it, Escape cancels, and
 * a screen reader announces it as the question it is. The Volto add-on keeps
 * its own Semantic UI modal; this is for a frontend without one.
 * @module components/ConfirmDialog/ConfirmDialog
 */
import React from 'react';
import { Dialog, Heading, Modal, ModalOverlay } from 'react-aria-components';

import { defineMessages } from '#i18n';

import { useIdentityUI } from '../IdentityUI/IdentityUI';

import './ConfirmDialog.css';

const messages = defineMessages({
  cancel: { id: 'Cancel', defaultMessage: 'Cancel' },
});

export interface ConfirmDialogProps {
  isOpen: boolean;
  /** What is being decided about. */
  title: string;
  /** What happens if it goes ahead. */
  message: string;
  /** The button that goes ahead: named for what it does. */
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
}) => {
  const { t } = useIdentityUI();
  return (
    <ModalOverlay
      className="identity-confirm-overlay"
      isOpen={isOpen}
      isDismissable
      onOpenChange={(open) => {
        if (!open) {
          onCancel();
        }
      }}
    >
      <Modal className="identity-confirm-modal">
        <Dialog
          role="alertdialog"
          className="identity-confirm identity-surface"
        >
          <Heading slot="title" className="identity-surface__header">
            {title}
          </Heading>
          <p className="identity-confirm__message">{message}</p>
          <div className="identity-confirm__actions">
            <button
              type="button"
              className="identity-button"
              onClick={onCancel}
            >
              {t(messages.cancel)}
            </button>
            <button
              type="button"
              className="identity-button identity-button--danger"
              data-action="confirm"
              onClick={onConfirm}
            >
              {confirmLabel}
            </button>
          </div>
        </Dialog>
      </Modal>
    </ModalOverlay>
  );
};

export default ConfirmDialog;

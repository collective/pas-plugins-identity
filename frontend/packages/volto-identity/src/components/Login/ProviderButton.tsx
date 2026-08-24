/**
 * One button in the list of ways in.
 *
 * Presentational, and deliberately not tied to a `LoginProvider`: the local
 * password is offered as one of these too, wearing `volto-authomatic`'s Plone
 * colours, and it is not a provider the backend knows anything about. The
 * caller supplies the label, the driver whose colours to wear, and what
 * pressing it does.
 * @module components/Login/ProviderButton
 */
import React from 'react';

import './ProviderButton.scss';

interface ProviderButtonProps {
  /** Whose colours to wear. `plone` is the local password form. */
  driver: string;
  /**
   * What the button says.
   *
   * A provider's own title, which an operator sets and which is therefore not
   * ours to translate; the caller translates its own labels.
   */
  label: string;
  /** The provider id, for anything selecting this button by it. */
  id?: string;
  disabled?: boolean;
  onSelect: () => void;
}

const ProviderButton: React.FC<ProviderButtonProps> = ({
  driver,
  label,
  id,
  disabled = false,
  onSelect,
}) => (
  <button
    type="button"
    className={`identity-provider identity-provider--${driver}`}
    data-provider={id}
    disabled={disabled}
    onClick={onSelect}
  >
    {label}
  </button>
);

export default ProviderButton;

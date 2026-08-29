/**
 * One button in the list of ways in.
 *
 * Presentational, and deliberately not tied to a `LoginProvider`: the local
 * password is offered as one of these too, wearing `volto-authomatic`'s Plone
 * colours, and it is not a provider the backend knows anything about. The
 * caller supplies the label, the driver whose colours to wear, and what
 * pressing it does.
 *
 * A provider may also carry its *own* look -- an icon and two colours an
 * operator set in the control panel. When it does, that wins over the
 * driver's stylesheet class, because the operator has said what this button
 * should look like and the class is only a default for the ones who have not.
 * @module components/Login/ProviderButton
 */
import React from 'react';

import type { ProviderStyle } from '../../types';

import './ProviderButton.scss';

interface ProviderButtonProps extends ProviderStyle {
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
  icon,
  background_color: background,
  foreground_color: foreground,
  disabled = false,
  onSelect,
}) => {
  // Only the colours that were set. Writing `undefined` into a style object
  // is harmless, but writing an empty string is not: it produces
  // `background-color: ` in the attribute, which some engines treat as a
  // reset of the inherited value rather than as nothing at all.
  const style: React.CSSProperties = {};
  if (background) {
    style.backgroundColor = background;
  }
  if (foreground) {
    style.color = foreground;
  }
  const styled = Boolean(background || foreground);

  return (
    <button
      type="button"
      className={[
        'identity-provider',
        `identity-provider--${driver}`,
        // Marks the button as carrying its own colours, so the stylesheet can
        // stand back rather than fight an inline style with specificity.
        styled ? 'identity-provider--styled' : '',
      ]
        .filter(Boolean)
        .join(' ')}
      style={styled ? style : undefined}
      data-provider={id}
      disabled={disabled}
      onClick={onSelect}
    >
      {icon ? (
        <span
          className="identity-provider__icon"
          aria-hidden="true"
          // The source is an SVG document the backend sanitized as it was
          // stored: an allowlist of elements and attributes, no attribute
          // that references a URL, and the whole thing serialized from the
          // parsed tree rather than sliced out of what was pasted. Inlining
          // it rather than using an `<img>` is what lets it inherit the
          // button's colour, which is the entire reason an operator uploads
          // one.
          dangerouslySetInnerHTML={{ __html: icon }}
        />
      ) : null}
      <span className="identity-provider__label">{label}</span>
    </button>
  );
};

export default ProviderButton;

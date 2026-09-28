/**
 * A number, and what it counts.
 *
 * `42 members`, `12 directly`: the figure set apart from the words, so a row
 * of them reads as figures first. The label is already translated by the
 * caller, which is the only one who knows whether it needs the number for a
 * plural -- `{count, plural, one {member} other {members}}` -- or not.
 *
 * The number is formatted for the reader's locale, so a large group reads as
 * `1,234` in English and `1.234` in German.
 * @module components/Count/Count
 */
import React from 'react';
import { useIntl } from 'react-intl';

import './Count.scss';

export interface CountProps {
  /** The figure. */
  value: number;
  /** What it counts, translated. */
  label: string;
  /** Quieter, for a figure that qualifies another beside it. */
  secondary?: boolean;
}

const Count: React.FC<CountProps> = ({ value, label, secondary = false }) => {
  const intl = useIntl();
  return (
    <div
      className={
        secondary
          ? 'identity-count identity-count--secondary'
          : 'identity-count'
      }
    >
      <span className="identity-count__value">{intl.formatNumber(value)}</span>{' '}
      <span className="identity-count__label">{label}</span>
    </div>
  );
};

export default Count;

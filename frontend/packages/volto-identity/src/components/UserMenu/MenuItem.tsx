/**
 * One entry in the personal-tools menu.
 *
 * Every entry in that menu is the same thing -- a label, a right arrow, and
 * either a route to go to or a panel to slide in -- and there are now five of
 * them, each registered separately so a site can reorder or remove any one.
 * Written once here so that "the same thing" stays true: five copies of this
 * markup would drift, and the menu's stylesheet keys on it.
 *
 * It renders the `<li>` because it lands inside the menu's own `<ul>`.
 * @module components/UserMenu/MenuItem
 */
import React from 'react';
import { Link } from 'react-router-dom';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import rightArrowSVG from '@plone/volto/icons/right-key.svg';

interface MenuItemProps {
  /** DOM id, so a stylesheet or a test can name this entry. */
  id: string;
  /** The visible label, already translated. */
  label: string;
  /** Where it goes. Mutually exclusive with `onClick`. */
  to?: string;
  /** What it does instead of going anywhere -- sliding a panel in. */
  onClick?: () => void;
}

const MenuItem: React.FC<MenuItemProps> = ({ id, label, to, onClick }) => (
  <li>
    {to ? (
      <Link id={id} to={to}>
        {label}
        <Icon name={rightArrowSVG} size="24px" />
      </Link>
    ) : (
      // `aria-label` as well as the text: the arrow is inside the button, and
      // an accessible name assembled from the label plus an icon's title is
      // what a screen reader would otherwise read out.
      <button id={id} aria-label={label} onClick={onClick}>
        {label}
        <Icon name={rightArrowSVG} size="24px" />
      </button>
    )}
  </li>
);

export default MenuItem;

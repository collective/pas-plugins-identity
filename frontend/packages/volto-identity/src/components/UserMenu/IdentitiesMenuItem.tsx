/**
 * A link into the identities view, plugged into Volto's user menu.
 * @module components/UserMenu/IdentitiesMenuItem
 */
import React from 'react';
import { Link } from 'react-router-dom';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import { Plug } from '@plone/volto/components/manage/Pluggable';
import rightArrowSVG from '@plone/volto/icons/right-key.svg';

import { IDENTITIES_PATH } from '../../config/routes';

/**
 * Volto's `PersonalTools` ends its menu list with a `toolbar-user-menu`
 * pluggable, which is the supported way to add an entry without shadowing the
 * component. The plug renders an `<li>` because it lands inside that list's
 * `<ul>`, and carries the same right-arrow icon as the entries beside it so it
 * does not read as a different kind of thing.
 */
const IdentitiesMenuItem: React.FC = () => (
  <Plug pluggable="toolbar-user-menu" id="identities">
    <li>
      <Link id="toolbar-identities" to={IDENTITIES_PATH}>
        Sign-in methods
        <Icon name={rightArrowSVG} size="24px" />
      </Link>
    </li>
  </Plug>
);

export default IdentitiesMenuItem;

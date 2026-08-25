/**
 * A link into the identities view, plugged into Volto's user menu.
 * @module components/UserMenu/IdentitiesMenuItem
 */
import React from 'react';
import { defineMessages, useIntl } from 'react-intl';
import { Plug } from '@plone/volto/components/manage/Pluggable';

import { IDENTITIES_PATH } from '../../config/routes';
import MenuItem from './MenuItem';

const messages = defineMessages({
  title: { id: 'Sign-in methods', defaultMessage: 'Sign-in methods' },
});

/**
 * Ordered right after Preferences, because it is one: this is where a person
 * adds a way of getting in or drops one they no longer use. See
 * :mod:`components/UserMenu/UserMenuPlugs` for the whole ordering.
 */
const IdentitiesMenuItem: React.FC = () => {
  const intl = useIntl();
  return (
    <Plug pluggable="toolbar-user-menu" id="identities" order={30}>
      <MenuItem
        id="toolbar-identities"
        label={intl.formatMessage(messages.title)}
        to={IDENTITIES_PATH}
      />
    </Plug>
  );
};

export default IdentitiesMenuItem;

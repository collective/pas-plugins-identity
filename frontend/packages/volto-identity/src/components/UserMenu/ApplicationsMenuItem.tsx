/**
 * A link to the authorized-applications page, plugged into Volto's user menu.
 *
 * Ordered right after "Sign-in methods", because it is the same question
 * asked the other way round: that entry is what you sign in *with*, this one
 * is what you have signed in *to*. Between it and Site Setup, which the
 * ten-spaced orders in :mod:`components/UserMenu/UserMenuPlugs` exist to
 * allow without renumbering anything.
 *
 * **Shown only where it leads somewhere.** `@oauth-grants` is published by
 * the `[server]` layer alone, so on a site that never became an
 * authorization server the route would render a page that can only report a
 * failure. There is nothing in the user payload that says whether that layer
 * is installed -- `core` may not depend on `server`, so its serializer
 * cannot mention it -- and rather than reach across that boundary this asks
 * the endpoint itself, once, and shows the entry when it answered.
 *
 * The cost is one request per session: on a site with the layer it is the
 * data the page needs anyway, and on a site without it, one 404 that nobody
 * sees. The alternative was a menu entry leading to an error page, which is
 * the thing this package has refused everywhere else.
 * @module components/UserMenu/ApplicationsMenuItem
 */
import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { defineMessages, useIntl } from 'react-intl';
import { Plug } from '@plone/volto/components/manage/Pluggable';

import { listGrants } from '../../actions';
import { APPLICATIONS_PATH } from '../../config/routes';
import MenuItem from './MenuItem';

const messages = defineMessages({
  title: { id: 'Applications', defaultMessage: 'Applications' },
});

const ApplicationsMenuItem: React.FC = () => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const userid = useSelector((state: any) => state.userProfile?.data?.id);
  const loaded = useSelector((state: any) =>
    Boolean(state.oauthGrants?.loaded),
  );
  const pending = useSelector((state: any) =>
    Boolean(state.oauthGrants?.loading),
  );
  const failed = useSelector((state: any) => Boolean(state.oauthGrants?.error));

  useEffect(() => {
    // Only once somebody is signed in: anonymous has authorized nothing, and
    // asking would be a guaranteed 401 on every anonymous page view.
    //
    // `loaded` and `error` both stop it. A site without the `[server]` layer
    // answers 404, and retrying that on every render would be a request loop
    // rather than a feature detection.
    if (!userid || loaded || pending || failed) {
      return;
    }
    dispatch(listGrants());
  }, [dispatch, userid, loaded, pending, failed]);

  if (!loaded) {
    return null;
  }

  return (
    <Plug
      pluggable="toolbar-user-menu"
      id="applications"
      order={35}
      dependencies={[loaded]}
    >
      <MenuItem
        id="toolbar-applications"
        label={intl.formatMessage(messages.title)}
        to={APPLICATIONS_PATH}
      />
    </Plug>
  );
};

export default ApplicationsMenuItem;

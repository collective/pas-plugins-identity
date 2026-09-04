/**
 * One user's account, as a page in the control panel.
 *
 * The store and the routing around `UserAccountPanel`, which is the same
 * split every other page here uses: the panel renders what it is given, this
 * decides who it is about and asks for them.
 *
 * The userid comes off the route rather than from a row's props, which is the
 * whole reason this exists. As a modal the panel could only ever be opened
 * from the row that fetched it -- so it could not be linked to, bookmarked,
 * opened in a new tab or reached with the back button, and an administrator
 * comparing two accounts had to close one to open the other.
 * @module components/ControlPanel/UserAccount
 */
import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Link, useLocation, useParams } from 'react-router-dom';
import { createPortal } from 'react-dom';
import { Container, Segment } from 'semantic-ui-react';
import { defineMessages, useIntl } from 'react-intl';

import { Helmet } from '@plone/volto/helpers/Helmet/Helmet';
import { useClient } from '@plone/volto/hooks/client/useClient';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import Toolbar from '@plone/volto/components/manage/Toolbar/Toolbar';
import backSVG from '@plone/volto/icons/back.svg';

import { getUserAccount } from '../../actions';
import UserAccountPanel from './UserAccountPanel';

/**
 * The userid a route match carries, as the userid it names.
 *
 * `useParams` hands back a segment react-router has only half decoded: it
 * turns `%20` into a space but leaves `%2F` alone, since a decoded slash
 * would no longer be one segment. `getUserAccount` escapes what it is given,
 * so passing that through unchanged encodes the `%` a second time and asks
 * the backend for a userid nobody has.
 *
 * @param value The raw route parameter.
 * @returns The userid, or the value unchanged when it is not valid escaping
 *   -- a userid may legitimately contain a bare `%`, and refusing to render
 *   the page over it would be worse than asking for it verbatim.
 */
export function decodeUserid(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

const messages = defineMessages({
  title: { id: 'Account', defaultMessage: 'Account' },
  back: { id: 'Back', defaultMessage: 'Back' },
});

/** Where the listing this page is reached from lives. */
const USERS_CONTROLPANEL = '/controlpanel/users';

const UserAccount: React.FC = () => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const isClient = useClient();
  const { pathname } = useLocation();
  const params = useParams<{ userid: string }>();
  const userid = params.userid ? decodeUserid(params.userid) : params.userid;

  const request = useSelector((state: any) => state.userAccount);

  useEffect(() => {
    if (userid) {
      (dispatch as any)(getUserAccount(userid));
    }
  }, [dispatch, userid]);

  // The slice holds one account at a time, and arriving here from another
  // user's page means last user's answer is still in it. Rendering that under
  // this person's name is the one mistake this page must not make -- so an
  // answer about somebody else is treated as no answer yet.
  const account = request?.data?.userid === userid ? request.data : null;
  const loading = Boolean(request?.loading) || (!account && !request?.error);

  // The account carries a name; until it arrives the userid is what we have,
  // and it is what the administrator clicked.
  const heading = account?.fullname || userid;

  return (
    // The chrome Volto's own control-panel pages have: a centring container,
    // a titled panel, and the toolbar with a way back to the listing.
    <Container id="page-user-account">
      <Helmet title={`${intl.formatMessage(messages.title)} — ${heading}`} />
      <Segment.Group raised>
        <Segment className="primary">{heading}</Segment>
        <Segment>
          <UserAccountPanel
            account={account}
            loading={loading}
            error={request?.error}
          />
        </Segment>
      </Segment.Group>
      {isClient &&
        createPortal(
          <Toolbar
            pathname={pathname}
            hideDefaultViewButtons
            inner={
              <Link to={USERS_CONTROLPANEL} className="item">
                <Icon
                  name={backSVG}
                  className="contents circled"
                  size="30px"
                  title={intl.formatMessage(messages.back)}
                />
              </Link>
            }
          />,
          document.getElementById('toolbar') as HTMLElement,
        )}
    </Container>
  );
};

export default UserAccount;

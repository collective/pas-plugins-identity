/**
 * The sign-in block for somebody signed in: who they are, and how they got in.
 *
 * What it says comes from `@user-account` about the caller, which a user may
 * read about themselves: their Profile, their addresses and their audit
 * events. The name they sign in with is the one thing that lacks, and
 * `UserProfileLoader` already keeps it in `userProfile` on every page.
 * @module components/Welcome/Welcome
 */
import React, { useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useIntl } from 'react-intl';
import { flattenToAppURL } from '@plone/volto/helpers/Url/Url';

import { getUserAccount } from '../../actions';
import { useridFromToken } from '../../helpers/token';
import {
  fillPlaceholders,
  providerTitle,
  recentSignIns,
  SIGN_IN_EVENTS,
} from '../../helpers/welcome';
import type { SignInBlockData, UserAccount, UserProfile } from '../../types';
import { defaultGreeting } from '../Blocks/SignIn/schema';
import WelcomeCard from './WelcomeCard';

interface WelcomeProps {
  /** The block's settings. */
  data: SignInBlockData;
}

const Welcome: React.FC<WelcomeProps> = ({ data }) => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const token = useSelector((state: any) => state.userSession?.token);
  const user: UserProfile | null = useSelector(
    (state: any) => state.userProfile?.data ?? null,
  );
  const request = useSelector((state: any) => state.userAccount);
  const userid = useridFromToken(token);
  const attempted = useRef<string | null>(null);

  // A switch the block never saved is on: a block added before a line
  // existed should show it, as a new one does.
  const showProfile = data.showProfile !== false;
  const showEmail = data.showEmail !== false;
  const showProvider = data.showProvider !== false;
  const showLastLogin = data.showLastLogin !== false;
  const wantsAccount =
    showProfile || showEmail || showProvider || showLastLogin;

  // The slice holds one account at a time, and the account page fills it
  // with whoever an administrator last looked at. An answer about somebody
  // else is no answer.
  const account: UserAccount | null =
    request?.data?.userid === userid ? request.data : null;

  useEffect(() => {
    if (!userid || !wantsAccount || account) {
      return;
    }
    // Once per userid, however it turns out. A failed request leaves nothing
    // here either, and asking again on every render is a request loop.
    if (attempted.current === userid) {
      return;
    }
    attempted.current = userid;
    dispatch(getUserAccount(userid, SIGN_IN_EVENTS));
  }, [dispatch, userid, wantsAccount, account]);

  const person = user?.id === userid ? user : null;
  const username = person?.username || userid;
  const fullname = person?.fullname || account?.fullname || username;
  const greeting = fillPlaceholders(data.greeting ?? defaultGreeting(intl), {
    username,
    fullname,
  });
  const { current, previous } = recentSignIns(account?.events ?? []);

  return (
    <WelcomeCard
      greeting={greeting}
      profile={
        showProfile && account?.profile_url
          ? { to: flattenToAppURL(account.profile_url), label: fullname }
          : null
      }
      email={
        showEmail
          ? account?.emails.find((address) => address.preferred) ?? null
          : null
      }
      provider={
        showProvider && current
          ? providerTitle(current.provider, account?.identities ?? [])
          : null
      }
      lastLogin={
        showLastLogin && previous
          ? intl.formatDate(previous.timestamp, {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
              hour: 'numeric',
              minute: '2-digit',
            })
          : null
      }
    />
  );
};

export default Welcome;

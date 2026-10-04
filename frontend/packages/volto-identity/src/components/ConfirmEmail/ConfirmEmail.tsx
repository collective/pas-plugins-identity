/**
 * Asking which verified address stands for the signed-in user.
 *
 * A site can ask this at a first sign-in that brought more than one verified
 * address. The backend holds the Profile `incomplete` until its owner answers,
 * and the edit form cannot answer for them: which address stands for somebody
 * is the order of their addresses, a sign-in writes that order too, and so only
 * an explicit answer through `@confirm-email` counts. `ProfileGate` and the
 * first-login route send a user here when that answer is the only thing their
 * Profile is waiting on.
 *
 * The card itself is `identity-core`'s `ConfirmEmailCard`, which the Aurora
 * add-on shows too; this is what Volto puts around it.
 *
 * It navigates nowhere once answered. The answer is `@my-profile` as it is
 * afterwards, the `myProfile` slice takes it in, and `ProfileGate` sees the
 * Profile released and returns the user to where they were going. A site that
 * does not mount the gate gets the confirmation and a way on.
 * @module components/ConfirmEmail/ConfirmEmail
 */
import React, { useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { defineMessages, useIntl } from 'react-intl';
import { Helmet } from '@plone/volto/helpers/Helmet/Helmet';

import { ConfirmEmailCard } from '@plone-collective/identity-core';
import type { ConfirmEmailStatus } from '@plone-collective/identity-core';
import { confirmEmail, getMyProfile } from '../../actions';
import type { ProfileEmail } from '../../types';
import VoltoIdentityUI from '../IdentityUI/VoltoIdentityUI';

const messages = defineMessages({
  title: {
    id: 'Confirm your email address',
    defaultMessage: 'Confirm your email address',
  },
});

const ConfirmEmail: React.FC = () => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const asked = useRef(false);

  const token = useSelector((state: any) => state.userSession?.token);
  const profile = useSelector((state: any) => state.myProfile);
  const confirmation = useSelector((state: any) => state.emailConfirmation);

  useEffect(() => {
    // Asked only when nobody has: `ProfileGate` asks on every navigation, and
    // this page still has to work on a site that does not mount the gate.
    // Remembered in a ref rather than read off `loaded`, which a failed
    // request never becomes -- that would ask again on every render.
    if (!token || asked.current || profile?.loaded || profile?.loading) {
      return;
    }
    asked.current = true;
    dispatch(getMyProfile());
  }, [dispatch, token, profile?.loaded, profile?.loading]);

  const recorded: string | undefined = confirmation?.loaded
    ? confirmation.data?.emails?.find((entry: ProfileEmail) => entry.preferred)
        ?.address
    : undefined;

  let status: ConfirmEmailStatus;
  if (recorded) {
    status = 'done';
  } else if (token && !profile?.loaded && !profile?.error) {
    status = 'loading';
  } else if (profile?.data?.confirm_email) {
    status = 'asking';
  } else {
    status = 'nothing';
  }

  return (
    // The page the first-login wait and the login page are: this is the last
    // step of the same flow.
    <div id="page-login">
      <Helmet title={intl.formatMessage(messages.title)} />
      <VoltoIdentityUI>
        <ConfirmEmailCard
          status={status}
          emails={profile?.data?.emails ?? []}
          recorded={recorded}
          busy={Boolean(confirmation?.loading)}
          failed={Boolean(confirmation?.error)}
          onConfirm={(address) => dispatch(confirmEmail(address))}
        />
      </VoltoIdentityUI>
    </div>
  );
};

export default ConfirmEmail;

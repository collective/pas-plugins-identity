/**
 * Holding a signed-in user on their profile until it is complete.
 *
 * The backend has a gate of its own, and it deliberately lets
 * `plone.restapi` requests through: Volto fetches the edit form over the API,
 * so gating those would break the page the user is being sent to. Every
 * navigation in this app is such a request, which means the backend gate
 * never fires for a Volto site and this component is where the same rule
 * lives.
 *
 * Wire it into `appExtras` so that it is mounted on every route:
 *
 * ```ts
 * config.settings.appExtras = [
 *   ...config.settings.appExtras,
 *   { match: '', component: ProfileGate },
 * ];
 * ```
 *
 * It does three things, and the second and third exist because the first one
 * on its own was a trap in the demo.
 *
 * 1. **Redirect**, while the profile is incomplete.
 * 2. **Say why.** A user dropped on an edit form with no explanation cannot
 *    tell a requirement from a broken site. The backend reports which fields
 *    are missing, so the message names them.
 * 3. **Come back.** The interruption happens mid-journey — in the demo, in
 *    the middle of signing in to *another* site through this one — and a user
 *    who fills the form in was left on their profile with no way onward. The
 *    destination is remembered before redirecting and restored the moment the
 *    profile stops being incomplete.
 *
 * The destination is not always this app's to remember. When the backend's
 * authorization endpoint pauses a federated sign-in at this form, it hands
 * the request to resume over as `return_url`, and that target is a backend
 * view rather than a route — so it is taken into the same memory on arrival
 * and resumed with a real navigation.
 *
 * The decision itself lives in `helpers/profileGate`, where it is tested
 * without a store.
 * @module components/ProfileGate/ProfileGate
 */
import React, { useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useHistory, useLocation } from 'react-router-dom';
import { defineMessages, useIntl } from 'react-intl';
import { addMessage } from '@plone/volto/actions';

import { getMyProfile } from '../../actions';
import {
  gateTarget,
  goTo,
  handedOverReturn,
  rememberReturn,
  takeReturn,
} from '../../helpers/profileGate';

const messages = defineMessages({
  title: {
    id: 'Complete your profile',
    defaultMessage: 'Complete your profile',
  },
  body: {
    id: 'Your profile needs a few more details before you can continue.',
    defaultMessage:
      'Your profile needs a few more details before you can continue.',
  },
  bodyWithFields: {
    id: 'Please fill in {fields} before you can continue.',
    defaultMessage: 'Please fill in {fields} before you can continue.',
  },
});

interface ProfileGateProps {
  /** Backend base URL, when it differs from the frontend's. */
  apiPath?: string;
}

const ProfileGate: React.FC<ProfileGateProps> = ({ apiPath = '' }) => {
  const dispatch = useDispatch();
  const history = useHistory();
  const location = useLocation();
  const intl = useIntl();
  const asked = useRef(false);
  const explained = useRef(false);

  const token = useSelector((state: any) => state.userSession?.token);
  const profile = useSelector((state: any) => state.myProfile);

  useEffect(() => {
    // Anonymous users have no profile to be held for, and asking would answer
    // 401 on every page of a public site.
    if (!token) {
      return;
    }
    // Re-asked on every navigation, not once: saving the form is a navigation,
    // and a stale answer here is a user held on a profile they have already
    // completed.
    asked.current = true;
    dispatch(getMyProfile());
  }, [dispatch, token, location.pathname]);

  useEffect(() => {
    if (!token || !profile?.loaded || profile?.error) {
      // Not yet, or not at all. A backend that cannot answer must not be able
      // to make the site unreachable: the worst case of letting somebody
      // through is that they fill their profile in later.
      return;
    }

    // Whether the *profile* is unfinished, which is not the same question as
    // whether this page would be redirected. Keying the return on `gateTarget`
    // instead is an infinite loop: the gate sends the user to their profile,
    // and being on their profile makes `gateTarget` answer null, which reads
    // as "they finished" and sends them straight back.
    // A destination handed over by the backend. The authorization endpoint
    // pauses its own request at this form and passes it as `return_url`;
    // taking it into the same memory means one way back rather than two.
    const handedOver = handedOverReturn(location.search);
    if (handedOver) {
      rememberReturn(handedOver);
    }

    const held =
      !!profile.data?.profile && profile.data.review_state === 'incomplete';

    if (!held) {
      // Finished, or never unfinished. If they were held earlier, this is the
      // moment they completed it, so send them on to where they were going.
      const back = takeReturn();
      if (back && back !== location.pathname) {
        goTo(back, history.replace);
      }
      return;
    }

    const target = gateTarget(profile.data, location.pathname, apiPath);

    if (target && target !== location.pathname) {
      rememberReturn(`${location.pathname}${location.search}`);
      if (!explained.current) {
        explained.current = true;
        const missing = profile.data?.missing ?? [];
        dispatch(
          addMessage(
            intl.formatMessage(messages.title),
            missing.length
              ? intl.formatMessage(messages.bodyWithFields, {
                  fields: missing.join(', '),
                })
              : intl.formatMessage(messages.body),
            'warning',
          ),
        );
      }
      history.replace(target);
    }
  }, [
    profile,
    location.pathname,
    location.search,
    history,
    apiPath,
    dispatch,
    intl,
    token,
  ]);

  return null;
};

export default ProfileGate;

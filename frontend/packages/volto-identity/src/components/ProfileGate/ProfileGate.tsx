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
 * It renders nothing. What it does is decide, and the decision itself lives
 * in `helpers/profileGate` where it can be tested without a store.
 * @module components/ProfileGate/ProfileGate
 */
import React, { useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useHistory, useLocation } from 'react-router-dom';

import { getMyProfile } from '../../actions';
import { gateTarget } from '../../helpers/profileGate';

interface ProfileGateProps {
  /** Backend base URL, when it differs from the frontend's. */
  apiPath?: string;
}

const ProfileGate: React.FC<ProfileGateProps> = ({ apiPath = '' }) => {
  const dispatch = useDispatch();
  const history = useHistory();
  const location = useLocation();
  const asked = useRef(false);

  const token = useSelector((state: any) => state.userSession?.token);
  const profile = useSelector((state: any) => state.myProfile);

  useEffect(() => {
    // Anonymous users have no profile to be held for, and asking would answer
    // 401 on every page of a public site.
    if (!token || asked.current) {
      return;
    }
    asked.current = true;
    dispatch(getMyProfile());
  }, [dispatch, token]);

  useEffect(() => {
    if (!profile?.loaded || profile?.error) {
      // Not yet, or not at all. A backend that cannot answer must not be able
      // to make the site unreachable: the worst case of letting somebody
      // through is that they fill their profile in later.
      return;
    }
    const target = gateTarget(profile.data, location.pathname, apiPath);
    if (target && target !== location.pathname) {
      history.replace(target);
    }
  }, [profile, location.pathname, history, apiPath]);

  return null;
};

export default ProfileGate;

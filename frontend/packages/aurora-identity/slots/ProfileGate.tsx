/**
 * Holding a signed-in user until their profile is complete.
 *
 * The decision is `lib/gate`'s; this carries it out. Rendered in Aurora's
 * `authenticatedTools` slot, so on every page a signed-in user sees the
 * site's header on, and it draws nothing.
 *
 * Like the Volto add-on's gate, it remembers where the user was going before
 * sending them on, and takes them back there once the profile stops being
 * incomplete -- which is the moment saving the edit form lands them on their
 * profile. A destination the backend's authorization endpoint hands over, a
 * sign-in to another site paused at this profile, is remembered the same way.
 * @module slots/ProfileGate
 */
import { useEffect } from 'react';
import { useLocation, useNavigate, useRouteLoaderData } from 'react-router';
import {
  CONFIRM_EMAIL_PATH,
  goTo,
  handedOverReturn,
  onProfile,
  rememberReturn,
  takeReturn,
} from '@plone-collective/identity-core';
import type { MyProfile } from '@plone-collective/identity-core';

import {
  COMPLETE_PROFILE_PATH,
  gateTarget,
  isHeld,
  PROFILE_KEY,
} from '../lib/gate';

export default function ProfileGate() {
  const root = useRouteLoaderData('root') as
    Record<string, unknown> | undefined;
  const profile = root?.[PROFILE_KEY] as MyProfile | undefined;
  const { pathname, search } = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    // No answer, no gate: a backend that cannot say must not be able to
    // lock anybody out.
    if (!profile) {
      return;
    }
    const replace = (path: string) => navigate(path, { replace: true });
    const handedOver = handedOverReturn(search);
    if (handedOver) {
      rememberReturn(handedOver);
    }

    if (!isHeld(profile)) {
      // Finished, or never held. If they were held earlier, this is the
      // moment they finished: on to where they were going.
      const back = takeReturn();
      if (back && back !== pathname) {
        goTo(back, replace);
      }
      return;
    }

    const target = gateTarget(profile, pathname);
    if (target && target !== pathname) {
      // Not from anywhere the hold itself sends people: that would replace
      // where they were going with one of the gate's own stops.
      if (
        !onProfile(profile, pathname) &&
        pathname !== CONFIRM_EMAIL_PATH &&
        pathname !== COMPLETE_PROFILE_PATH
      ) {
        rememberReturn(`${pathname}${search}`);
      }
      replace(target);
    }
  }, [profile, pathname, search, navigate]);

  return null;
}

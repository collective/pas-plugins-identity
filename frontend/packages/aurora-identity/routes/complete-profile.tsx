/**
 * Why a signed-in user is held, and the way to their profile's form.
 *
 * Where the profile gate sends a user whose profile is missing required
 * fields: `identity-core`'s `CompleteProfileCard`, naming them by the labels
 * the form gives them.
 * @module routes/complete-profile
 */
import { useLoaderData } from 'react-router';
import type { LoaderFunctionArgs } from 'react-router';
import {
  redirectWithClearedCookie,
  requireAuthCookie,
} from '@plone/react-router';
import { Container } from '@plone/quanta';
import {
  CompleteProfileCard,
  endpoints,
} from '@plone-collective/identity-core';
import type { MyProfile } from '@plone-collective/identity-core';

import AuroraIdentityUI from '../components/IdentityUI/AuroraIdentityUI';
import { callBackend } from '../lib/api';
import { COMPLETE_PROFILE_PATH, isHeld, profileEditPath } from '../lib/gate';

export async function loader({ request }: LoaderFunctionArgs) {
  const token = await requireAuthCookie(request);
  const answer = await callBackend(request, endpoints.myProfile(), { token });
  if (answer.status === 401) {
    throw await redirectWithClearedCookie(
      `/login?came_from=${encodeURIComponent(COMPLETE_PROFILE_PATH)}`,
    );
  }
  const me: Partial<MyProfile> = answer.ok ? await answer.json() : {};
  const titles = me.missing_titles ?? {};
  return {
    held: isHeld(me as MyProfile),
    // The labels the form gives the fields, where the backend sent them.
    missing: (me.missing ?? []).map((name) => titles[name] ?? name),
    editHref: me.profile ? profileEditPath(me.profile) : null,
  };
}

export default function CompleteProfile() {
  const { held, missing, editHref } = useLoaderData<typeof loader>();
  return (
    <AuroraIdentityUI>
      <Container width="default" className="identity-complete-profile-page">
        <CompleteProfileCard
          held={held}
          missing={missing}
          editHref={editHref}
        />
      </Container>
    </AuroraIdentityUI>
  );
}

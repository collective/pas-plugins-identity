/**
 * Keep the signed-in user's profile in the store.
 *
 * Volto fetches the current user only when the personal-tools menu opens, and
 * what it fetches lands in `state.users.user`, which the menu also clears
 * around itself. Anything that wants to show who is signed in *outside* that
 * menu -- an avatar in the toolbar, a link to the user's Profile -- therefore
 * cannot rely on it being there.
 *
 * This mounts on every route through `appExtras`, renders nothing, and asks
 * once per userid. It is the userid rather than the token that it keys on:
 * a token is reissued on refresh without the user changing, and refetching
 * the same person on every renewal would be a request per hour for nothing.
 * @module components/UserMenu/UserProfileLoader
 */
import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';

import { getUserProfile } from '../../actions';
import { useridFromToken } from '../../helpers/token';

const UserProfileLoader: React.FC = () => {
  const dispatch = useDispatch();
  const token = useSelector((state: any) => state.userSession?.token);
  const loadedFor = useSelector((state: any) => state.userProfile?.data?.id);
  const loading = useSelector((state: any) => state.userProfile?.loading);
  const userid = useridFromToken(token);

  useEffect(() => {
    // Anonymous, or already holding this user. A request in flight counts as
    // holding them: without that check the effect fires again on the render
    // the pending state causes, and the two answers race.
    if (!userid || loading || loadedFor === userid) {
      return;
    }
    dispatch(getUserProfile(userid));
  }, [dispatch, userid, loadedFor, loading]);

  return null;
};

export default UserProfileLoader;

/**
 * Change who is in a group: `<group>/manage-members`.
 *
 * Every request goes to an endpoint that already exists:
 *
 * - the members are read from `@group-members/<id>?direct=1`, a page at a
 *   time, which also says whether the caller may change them;
 * - people and groups are found with plone.restapi's `@users?search=` and
 *   `@groups?query=`, through Volto's own `listUsers` and `listGroups`;
 * - they are added, and people removed, with plone.restapi's
 *   `PATCH @groups/<id>`, through Volto's own `updateGroup`;
 * - a nested group is removed by writing its own `group_ids`, because
 *   `PATCH @groups/<id>` cannot -- see `unnestGroup`.
 *
 * Who may: whoever plone.restapi lets change a group's members, which is the
 * site-wide permission to manage users and groups, and for a group holding
 * the `Manager` role, a Manager. The listing's `can_manage` answers that, so
 * the page refuses before anybody tries.
 *
 * A route rather than a content view, as Volto's own sharing page is: the
 * group is the content Volto loaded for the URL without `/manage-members`,
 * which `nonContentRoutes` strips.
 * @module components/ManageMembers/ManageMembers
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Link, useLocation } from 'react-router-dom';
import { createPortal } from 'react-dom';
import { Container } from 'semantic-ui-react';
import { defineMessages, useIntl } from 'react-intl';
import { toast } from 'react-toastify';

import { Helmet } from '@plone/volto/helpers/Helmet/Helmet';
import { useClient } from '@plone/volto/hooks/client/useClient';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import Toolbar from '@plone/volto/components/manage/Toolbar/Toolbar';
import Toast from '@plone/volto/components/manage/Toast/Toast';
import { getBaseUrl, flattenToAppURL } from '@plone/volto/helpers/Url/Url';
import { listGroups, updateGroup } from '@plone/volto/actions/groups/groups';
import { listUsers } from '@plone/volto/actions/users/users';
import backSVG from '@plone/volto/icons/back.svg';

import { listDirectGroupMembers, unnestGroup } from '../../actions';
import { useMemberQuery } from '../Views/GroupsView/MemberSearch';
import { useMemberPage } from '../Views/GroupsView/MembersPagination';
import ManageMembersPanel from './ManageMembersPanel';
import type { Candidate } from './AddMembers';
import type { GroupMember, GroupMembers } from '../../types';

/** The last segment of the page's URL, after the group's own. */
export const MANAGE_MEMBERS_VIEW = 'manage-members';

/** How many people and how many groups a search for candidates offers. */
const CANDIDATE_LIMIT = 10;

const messages = defineMessages({
  back: { id: 'Back', defaultMessage: 'Back' },
  added: { id: 'manage-members-added', defaultMessage: 'Members added' },
  removed: { id: 'manage-members-removed', defaultMessage: 'Member removed' },
  error: { id: 'Error', defaultMessage: 'Error' },
});

/**
 * Turn Volto's search results into candidates to add.
 *
 * @param users `state.users.users`, from `@users?search=`.
 * @param groups `state.groups.groups`, from `@groups?query=`.
 * @returns Groups first, then people.
 */
export function toCandidates(users: any[], groups: any[]): Candidate[] {
  return [
    ...(groups ?? []).slice(0, CANDIDATE_LIMIT).map((group) => ({
      id: group.id,
      title: group.title || group.id,
      type: 'group' as const,
    })),
    ...(users ?? []).map((user) => ({
      id: user.id,
      title: user.fullname || user.username || user.id,
      type: 'user' as const,
      detail: user.username || user.email || undefined,
    })),
  ];
}

const ManageMembers: React.FC = () => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const isClient = useClient();
  const { pathname } = useLocation();
  const query = useMemberQuery();
  const page = useMemberPage();

  const content = useSelector((state: any) => state.content?.data);
  const listing = useSelector((state: any) => state.groupDirectMembers);
  const users = useSelector((state: any) => state.users?.users);
  const groups = useSelector((state: any) => state.groups?.groups);
  const searchingUsers = useSelector((state: any) =>
    Boolean(state.users?.list?.loading),
  );
  const searchingGroups = useSelector((state: any) =>
    Boolean(state.groups?.list?.loading),
  );

  const groupId: string | undefined = content?.id;
  const [candidateQuery, setCandidateQuery] = useState('');
  const [busy, setBusy] = useState(false);
  const [removing, setRemoving] = useState<string | null>(null);
  // Bumped after every change, so the page is read again from the server
  // rather than patched locally.
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (groupId) {
      dispatch(listDirectGroupMembers(groupId, query, page));
    }
  }, [dispatch, groupId, query, page, version]);

  const onCandidateQuery = useCallback(
    (next: string) => {
      setCandidateQuery(next);
      if (next) {
        // `search` rather than `query`: plone.restapi matches `query` against
        // the user id alone, and `search` against the name and email too, as
        // Volto's users control panel searches.
        dispatch(listUsers({ search: next, limit: CANDIDATE_LIMIT }));
        dispatch(listGroups(next));
      }
    },
    [dispatch],
  );

  /**
   * Send a change and report on it.
   *
   * @param action What to dispatch.
   * @param success The toast title when it worked.
   * @returns Once it has been reported.
   */
  const send = useCallback(
    (action: any, success: string) =>
      Promise.resolve(dispatch(action))
        .then(() => {
          toast.success(<Toast success title={success} />);
          setVersion((v) => v + 1);
        })
        .catch((err: any) => {
          toast.error(
            <Toast
              error
              title={intl.formatMessage(messages.error)}
              content={
                err?.response?.body?.message ??
                err?.response?.body?.error?.message ??
                String(err)
              }
            />,
          );
        }),
    [dispatch, intl],
  );

  const onAdd = useCallback(
    (selected: Candidate[]) => {
      if (!groupId || !selected.length) {
        return;
      }
      setBusy(true);
      const members = Object.fromEntries(selected.map((c) => [c.id, true]));
      send(
        updateGroup(groupId, { users: members }),
        intl.formatMessage(messages.added),
      ).finally(() => setBusy(false));
    },
    [groupId, send, intl],
  );

  const onRemove = useCallback(
    (member: GroupMember) => {
      if (!groupId) {
        return;
      }
      setRemoving(member.id);
      const action =
        member.type === 'group' && member.profile_url
          ? unnestGroup(
              flattenToAppURL(member.profile_url),
              member.through.filter((g) => g !== groupId),
            )
          : updateGroup(groupId, { users: { [member.id]: false } });
      send(action, intl.formatMessage(messages.removed)).finally(() =>
        setRemoving(null),
      );
    },
    [groupId, send, intl],
  );

  // A page for another group, or one still on its way, is not this one.
  const result: GroupMembers | null =
    !listing?.loading && listing?.data?.group === groupId ? listing.data : null;
  const refused =
    Boolean(listing?.error) || (result ? !result.can_manage : false);
  const title = content?.title || groupId || '';

  return (
    <Container id="page-manage-members">
      <Helmet title={title} />
      <ManageMembersPanel
        title={title}
        groupId={groupId ?? ''}
        groupUrl={content?.['@id'] ?? getBaseUrl(pathname)}
        result={result}
        refused={refused}
        query={query}
        candidateQuery={candidateQuery}
        onCandidateQuery={onCandidateQuery}
        candidates={candidateQuery ? toCandidates(users, groups) : []}
        searching={searchingUsers || searchingGroups}
        busy={busy}
        onAdd={onAdd}
        removing={removing}
        onRemove={onRemove}
      />
      {isClient &&
        createPortal(
          <Toolbar
            pathname={pathname}
            hideDefaultViewButtons
            inner={
              <Link to={`${getBaseUrl(pathname)}`} className="item">
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

export default ManageMembers;

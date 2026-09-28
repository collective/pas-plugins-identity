/**
 * What a group looks like when somebody opens it.
 *
 * A group is content, so it rendered through Volto's default view: a title
 * and an empty body. What a group page has to say is who is in it and what it
 * contains, and neither is on the content object -- membership is stored on
 * each member, and the nesting is a graph the backend closes over.
 *
 * So the page is the content object for its title and description, and
 * `@group-members/<id>` for everything else: how many people are in the
 * group, directly and in all, the groups nested inside this one, and the
 * groups this one is nested inside.
 *
 * ## Members are searched, not listed
 *
 * The page says how big the group is and offers a search; it does not list
 * everybody. A group everybody is in is exactly the group whose list is
 * useless and expensive to draw, and what somebody opening a group page
 * usually wants to know is whether a particular person is in it.
 *
 * The search is answered into a store slot of its own: a request clears its
 * slot while it is pending, and the counts and the nesting stay on screen
 * while somebody types. The query itself is kept in the URL -- see
 * `MemberSearch`.
 *
 * It may refuse. Reading a group's membership needs `Manage users` or
 * membership of the group itself -- a member list is personal data about
 * other people -- and a visitor who can see the group without being in it
 * gets the title and description and nothing more. That is a page rather than
 * an error, which is why the refusal is rendered as a note instead of being
 * left to the error boundary.
 *
 * ## Slots
 *
 * `aboveContent` and `belowContent` wrap this view already, because Volto's
 * own `View` renders both around whatever it resolves. `belowTitle` is
 * rendered here, under the heading, by `BelowTitleSlot` -- nothing outside a
 * view can place anything inside it.
 * @module components/Views/GroupsView/GroupView
 */
import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { defineMessages, useIntl } from 'react-intl';
import { Container } from 'semantic-ui-react';

import { Helmet } from '@plone/volto/helpers/Helmet/Helmet';

import { listGroupMembers, searchGroupMembers } from '../../../actions';
import BelowTitleSlot from '../BelowTitleSlot';
import GroupLinks from './GroupLinks';
import MemberResults from './MemberResults';
import MemberSearch, { useMemberQuery } from './MemberSearch';
import MembersCount from './MembersCount';
import type { GroupContent, GroupMembers } from '../../../types';

import './GroupView.scss';

const messages = defineMessages({
  nested: {
    id: 'Groups in this group',
    defaultMessage: 'Groups in this group',
  },
  nestedHelp: {
    id: 'group-view-nested-help',
    defaultMessage:
      'Everybody in these groups is in this one as well, at any depth.',
  },
  partOf: { id: 'Part of', defaultMessage: 'Part of' },
  members: { id: 'Members', defaultMessage: 'Members' },
  noMembers: {
    id: 'group-view-no-members',
    defaultMessage: 'Nobody is in this group yet.',
  },
  refused: {
    id: 'group-view-refused',
    defaultMessage:
      'You can see this group but not who is in it. A membership list is ' +
      'visible to its own members and to somebody who manages users.',
  },
  loading: { id: 'group-view-loading', defaultMessage: 'Loading members…' },
});

interface GroupViewProps {
  content: GroupContent;
}

const GroupView: React.FC<GroupViewProps> = ({ content }) => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const summaryState = useSelector((store: any) => store.groupMembers);
  const searchState = useSelector((store: any) => store.groupMemberSearch);
  const groupId = content.id;
  const query = useMemberQuery();

  useEffect(() => {
    if (groupId) {
      dispatch(listGroupMembers(groupId));
    }
  }, [dispatch, groupId]);

  useEffect(() => {
    if (groupId && query) {
      dispatch(searchGroupMembers(groupId, query));
    }
  }, [dispatch, groupId, query]);

  const summary: GroupMembers | null = summaryState?.data ?? null;
  // The membership only, not the group itself: a group that is loading and a
  // group somebody may not read are two different pages, and only one of them
  // has anything to wait for.
  const refused = Boolean(summaryState?.error);
  // A result for another group, or one still on its way, is not an answer to
  // what is in the box.
  const result: GroupMembers | null =
    !searchState?.loading && searchState?.data?.group === groupId
      ? searchState.data
      : null;

  let members: React.ReactNode;
  if (refused) {
    members = (
      <p className="identity-note">{intl.formatMessage(messages.refused)}</p>
    );
  } else if (!summary) {
    members = (
      <p className="identity-note" role="status">
        {intl.formatMessage(messages.loading)}
      </p>
    );
  } else if (!summary.members_total) {
    members = (
      <p className="identity-note">{intl.formatMessage(messages.noMembers)}</p>
    );
  } else {
    members = (
      <>
        <MembersCount
          total={summary.members_total}
          direct={summary.direct_members_total}
        />
        <MemberSearch />
        <MemberResults groupId={groupId} query={query} result={result} />
      </>
    );
  }

  return (
    <Container className="view-wrapper identity-group-view">
      <Helmet title={content.title || content.id} />
      <h1 className="documentFirstHeading">{content.title || content.id}</h1>
      <BelowTitleSlot content={content} />
      {content.description ? (
        <p className="documentDescription">{content.description}</p>
      ) : null}

      <GroupLinks
        className="identity-group-view__parents"
        title={intl.formatMessage(messages.partOf)}
        groups={summary?.parent_groups ?? []}
      />
      <GroupLinks
        className="identity-group-view__nested"
        title={intl.formatMessage(messages.nested)}
        help={intl.formatMessage(messages.nestedHelp)}
        groups={summary?.nested_groups ?? []}
      />

      <section className="identity-group-view__members">
        <h2>{intl.formatMessage(messages.members)}</h2>
        {members}
      </section>
    </Container>
  );
};

export default GroupView;

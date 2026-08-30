/**
 * What a group looks like when somebody opens it.
 *
 * A group is content, so it rendered through Volto's default view: a title
 * and an empty body. What a group page has to say is who is in it and what it
 * contains, and neither is on the content object -- membership is stored on
 * each member, and the nesting is a graph the backend closes over.
 *
 * So the page is the content object for its title and description, and
 * `@group-members/<id>` for everything else. That endpoint answers in one
 * request: the members with enough per person to draw a row, the groups
 * nested inside this one, and the groups this one is nested inside.
 *
 * It may refuse. Reading a group's membership needs `Manage users` or
 * membership of the group itself -- a member list is personal data about
 * other people -- and a visitor who can see the group without being in it
 * gets the title and description and nothing more. That is a page rather than
 * an error, which is why the refusal is rendered as a note instead of being
 * left to the error boundary.
 * @module components/Views/GroupView
 */
import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { defineMessages, useIntl } from 'react-intl';
import { Container } from 'semantic-ui-react';
import { Link } from 'react-router-dom';

import { Helmet } from '@plone/volto/helpers/Helmet/Helmet';
import { flattenToAppURL } from '@plone/volto/helpers/Url/Url';

import { listGroupMembers } from '../../actions';
import type { GroupMember, NestedGroup } from '../../types';

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
  through: { id: 'group-view-through', defaultMessage: 'through {groups}' },
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

/** The fields this view reads off a serialized group. */
interface GroupContent {
  '@id': string;
  id: string;
  title?: string;
  description?: string;
}

interface GroupViewProps {
  content: GroupContent;
}

/**
 * Render one entry in a list of groups.
 *
 * @param group The group to link to.
 * @returns The list item.
 */
function groupItem(group: NestedGroup) {
  return (
    <li key={group.id} data-group={group.id}>
      {group.title || group.id}
    </li>
  );
}

const GroupView: React.FC<GroupViewProps> = ({ content }) => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const state = useSelector((store: any) => store.groupMembers);
  const groupId = content.id;

  useEffect(() => {
    if (groupId) {
      dispatch(listGroupMembers(groupId));
    }
  }, [dispatch, groupId]);

  const data = state?.data;
  // The membership only, not the group itself: a group that is loading and a
  // group somebody may not read are two different pages, and only one of them
  // has anything to wait for.
  const refused = Boolean(state?.error);
  const members: GroupMember[] = data?.items ?? [];
  const nested: NestedGroup[] = data?.nested_groups ?? [];
  const parents: NestedGroup[] = data?.parent_groups ?? [];

  return (
    <Container className="view-wrapper identity-group-view">
      <Helmet title={content.title || content.id} />
      <h1 className="documentFirstHeading">{content.title || content.id}</h1>
      {content.description ? (
        <p className="documentDescription">{content.description}</p>
      ) : null}

      {parents.length ? (
        <section className="identity-group-view__parents">
          <h2>{intl.formatMessage(messages.partOf)}</h2>
          <ul>{parents.map(groupItem)}</ul>
        </section>
      ) : null}

      {nested.length ? (
        <section className="identity-group-view__nested">
          <h2>{intl.formatMessage(messages.nested)}</h2>
          <p className="identity-note">
            {intl.formatMessage(messages.nestedHelp)}
          </p>
          <ul>{nested.map(groupItem)}</ul>
        </section>
      ) : null}

      <section className="identity-group-view__members">
        <h2>{intl.formatMessage(messages.members)}</h2>
        {refused ? (
          <p className="identity-note">
            {intl.formatMessage(messages.refused)}
          </p>
        ) : state?.loading ? (
          <p className="identity-note" role="status">
            {intl.formatMessage(messages.loading)}
          </p>
        ) : members.length ? (
          <ul className="identity-group-view__list">
            {members.map((member) => (
              <li key={member.id} data-userid={member.id}>
                {member.profile_url ? (
                  <Link to={flattenToAppURL(member.profile_url)}>
                    {member.fullname}
                  </Link>
                ) : (
                  <span>{member.fullname}</span>
                )}
                {/* Which group this person arrived through, when it was not
                    this one. A list that silently mixes direct members with
                    inherited ones is a list nobody can account for. */}
                {member.through.includes(groupId) ? null : (
                  <span className="identity-note">
                    {intl.formatMessage(messages.through, {
                      groups: member.through.join(', '),
                    })}
                  </span>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="identity-note">
            {intl.formatMessage(messages.noMembers)}
          </p>
        )}
      </section>
    </Container>
  );
};

export default GroupView;

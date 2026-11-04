/**
 * The members of one group, as somebody who may change them sees them.
 *
 * What a change acts on: the groups nested here and the people in this group
 * itself, a page at a time, with the same search box and the same Volto
 * pagination as the group's own page. People who are in the group only
 * through a nested group are not listed: they are removed from that group,
 * on its own page.
 *
 * Given everything rather than reading the store, so every state is a set
 * of props; `ManageMembers` is the page that loads and saves.
 * @module components/ManageMembers/ManageMembersPanel
 */
import React from 'react';
import { defineMessages, useIntl } from 'react-intl';
import { Link } from 'react-router-dom';
import { Button, Label } from 'semantic-ui-react';

import Icon from '@plone/volto/components/theme/Icon/Icon';
import { flattenToAppURL } from '@plone/volto/helpers/Url/Url';
import deleteSVG from '@plone/volto/icons/delete.svg';

import AddMembers from './AddMembers';
import type { AddMembersProps } from './AddMembers';
import MemberSearch from '../Views/GroupsView/MemberSearch';
import MembersPagination from '../Views/GroupsView/MembersPagination';
import type { GroupMember, GroupMembers } from '../../types';

import './ManageMembersPanel.scss';

const messages = defineMessages({
  title: {
    id: 'manage-members-title',
    defaultMessage: 'Members of {group}',
  },
  back: { id: 'manage-members-back', defaultMessage: 'Back to the group' },
  members: { id: 'manage-members-direct', defaultMessage: 'Direct members' },
  help: {
    id: 'manage-members-direct-help',
    defaultMessage:
      'People who are in this group through a nested group are removed ' +
      'from that group.',
  },
  loading: { id: 'group-view-loading', defaultMessage: 'Loading members…' },
  empty: {
    id: 'manage-members-empty',
    defaultMessage: 'Nobody is in this group itself yet.',
  },
  noMatch: {
    id: 'group-view-no-match',
    defaultMessage: 'Nobody in this group matches “{query}”.',
  },
  refused: {
    id: 'manage-members-refused',
    defaultMessage:
      'You cannot change who is in this group. That needs permission to ' +
      'manage users and groups.',
  },
  group: { id: 'manage-members-group', defaultMessage: 'Group' },
  removeLabel: {
    id: 'manage-members-remove-label',
    defaultMessage: 'Remove {name} from this group',
  },
});

export interface ManageMembersPanelProps
  extends Omit<AddMembersProps, 'query' | 'onQuery'> {
  /** The group's title. */
  title: string;
  /** The group's id. */
  groupId: string;
  /** The group's own page, for the way back. */
  groupUrl: string;
  /** A page of direct members, or null while it is on its way. */
  result: GroupMembers | null;
  /** Whether the caller may not change the members. */
  refused: boolean;
  /** What the member list is narrowed to. */
  query: string;
  /** What the add form searched for. */
  candidateQuery: string;
  /** Called with what the add form should search for. */
  onCandidateQuery: (query: string) => void;
  /** The member being removed, while that is being saved. */
  removing: string | null;
  /** Called with the member to remove. */
  onRemove: (member: GroupMember) => void;
}

const ManageMembersPanel: React.FC<ManageMembersPanelProps> = ({
  title,
  groupId,
  groupUrl,
  result,
  refused,
  query,
  candidateQuery,
  onCandidateQuery,
  candidates,
  searching,
  busy,
  onAdd,
  removing,
  onRemove,
}) => {
  const intl = useIntl();

  let body: React.ReactNode;
  if (refused) {
    body = (
      <p className="identity-note">{intl.formatMessage(messages.refused)}</p>
    );
  } else {
    let list: React.ReactNode;
    if (!result) {
      list = (
        <p className="identity-note" role="status">
          {intl.formatMessage(messages.loading)}
        </p>
      );
    } else if (!result.items.length) {
      list = (
        <p className="identity-note">
          {query
            ? intl.formatMessage(messages.noMatch, { query })
            : intl.formatMessage(messages.empty)}
        </p>
      );
    } else {
      list = (
        <>
          <ul className="identity-manage-members__list">
            {result.items.map((member) => (
              <li
                key={`${member.type}:${member.id}`}
                className="identity-manage-members__row"
                data-member={member.id}
              >
                <span className="identity-manage-members__name">
                  {member.profile_url ? (
                    <Link to={flattenToAppURL(member.profile_url)}>
                      {member.fullname}
                    </Link>
                  ) : (
                    member.fullname
                  )}
                  {member.type === 'group' ? (
                    <Label size="mini">
                      {intl.formatMessage(messages.group)}
                    </Label>
                  ) : null}
                  {member.login ? (
                    <span className="identity-note">{member.login}</span>
                  ) : null}
                </span>
                <Button
                  basic
                  icon
                  type="button"
                  className="identity-manage-members__remove"
                  disabled={busy || removing !== null}
                  loading={removing === member.id}
                  aria-label={intl.formatMessage(messages.removeLabel, {
                    name: member.fullname,
                  })}
                  title={intl.formatMessage(messages.removeLabel, {
                    name: member.fullname,
                  })}
                  onClick={() => onRemove(member)}
                >
                  <Icon name={deleteSVG} size="20px" />
                </Button>
              </li>
            ))}
          </ul>
          <MembersPagination total={result.items_total} />
        </>
      );
    }
    body = (
      <>
        <AddMembers
          query={candidateQuery}
          onQuery={onCandidateQuery}
          candidates={candidates.filter((c) => c.id !== groupId)}
          searching={searching}
          busy={busy}
          onAdd={onAdd}
        />
        <section className="identity-manage-members__members">
          <h2>{intl.formatMessage(messages.members)}</h2>
          <p className="identity-note">{intl.formatMessage(messages.help)}</p>
          <MemberSearch />
          {list}
        </section>
      </>
    );
  }

  return (
    <div className="identity-manage-members">
      <h1 className="documentFirstHeading">
        {intl.formatMessage(messages.title, { group: title })}
      </h1>
      <p>
        <Link to={flattenToAppURL(groupUrl)}>
          {intl.formatMessage(messages.back)}
        </Link>
      </p>
      {body}
    </div>
  );
};

export default ManageMembersPanel;

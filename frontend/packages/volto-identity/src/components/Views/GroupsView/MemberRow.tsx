/**
 * One person found in a group.
 *
 * Linked to their Profile when they have one. An account that predates the
 * add-on, or a site not keeping users as content, has nowhere to send the
 * reader, and the name is shown without a link.
 *
 * A person who is in the group through another one says which: a list that
 * silently mixes direct members with inherited ones is a list nobody can
 * account for.
 * @module components/Views/GroupsView/MemberRow
 */
import React from 'react';
import { defineMessages, useIntl } from 'react-intl';
import { Link } from 'react-router-dom';

import { flattenToAppURL } from '@plone/volto/helpers/Url/Url';

import type { GroupMember } from '../../../types';

import './MemberRow.scss';

const messages = defineMessages({
  through: { id: 'group-view-through', defaultMessage: 'through {groups}' },
});

export interface MemberRowProps {
  member: GroupMember;
  /** The group whose page this is. */
  groupId: string;
}

const MemberRow: React.FC<MemberRowProps> = ({ member, groupId }) => {
  const intl = useIntl();
  return (
    <li className="identity-member-row" data-userid={member.id}>
      {member.profile_url ? (
        <Link to={flattenToAppURL(member.profile_url)}>{member.fullname}</Link>
      ) : (
        <span>{member.fullname}</span>
      )}
      {member.through.includes(groupId) ? null : (
        <span className="identity-note">
          {intl.formatMessage(messages.through, {
            groups: member.through.join(', '),
          })}
        </span>
      )}
    </li>
  );
};

export default MemberRow;

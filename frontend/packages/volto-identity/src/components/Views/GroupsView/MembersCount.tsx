/**
 * How many people are in a group, and where they come from.
 *
 * `42 members · 12 directly · 30 through nested groups`. The total is what a
 * group page leads with instead of a list of everybody; the split says how
 * much of it the group holds itself and how much arrives through the groups
 * nested inside it.
 *
 * The split only says something when there is one: in a group with nothing
 * nested in it everybody is a direct member, and `8 members · 8 directly`
 * repeats itself.
 * @module components/Views/GroupsView/MembersCount
 */
import React from 'react';
import { defineMessages, useIntl } from 'react-intl';

import Count from '../../Count/Count';

import './MembersCount.scss';

const messages = defineMessages({
  members: {
    id: 'group-view-members-total',
    defaultMessage: '{count, plural, one {member} other {members}}',
  },
  direct: {
    id: 'group-view-direct-total',
    defaultMessage: 'directly',
  },
  inherited: {
    id: 'group-view-inherited-total',
    defaultMessage: 'through nested groups',
  },
});

export interface MembersCountProps {
  /** Everybody in the group, nested memberships included. */
  total: number;
  /** The members in the group itself rather than through another. */
  direct: number;
}

const MembersCount: React.FC<MembersCountProps> = ({ total, direct }) => {
  const intl = useIntl();
  return (
    <p className="identity-members-count">
      <Count
        value={total}
        label={intl.formatMessage(messages.members, { count: total })}
      />
      {direct !== total ? (
        <>
          <Count
            value={direct}
            label={intl.formatMessage(messages.direct)}
            secondary
          />
          <Count
            value={total - direct}
            label={intl.formatMessage(messages.inherited)}
            secondary
          />
        </>
      ) : null}
    </p>
  );
};

export default MembersCount;

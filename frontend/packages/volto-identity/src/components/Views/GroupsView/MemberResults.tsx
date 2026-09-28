/**
 * What a search of a group's members found.
 *
 * Every state under the search box: a hint before anybody has searched, a
 * status while the search is on its way, a note when nobody matched, and
 * the people found otherwise -- with a line saying so when there are more of
 * them than one page holds.
 *
 * Given the search rather than reading it from the store, so every one of
 * those states is a set of props. Deciding which answer belongs to which
 * query is the page's job.
 * @module components/Views/GroupsView/MemberResults
 */
import React from 'react';
import { defineMessages, useIntl } from 'react-intl';

import MemberRow from './MemberRow';
import type { GroupMembers } from '../../../types';

import './MemberResults.scss';

const messages = defineMessages({
  hint: {
    id: 'group-view-search-hint',
    defaultMessage: 'Search by name or login to find somebody in this group.',
  },
  searching: { id: 'group-view-searching', defaultMessage: 'Searching…' },
  noMatch: {
    id: 'group-view-no-match',
    defaultMessage: 'Nobody in this group matches “{query}”.',
  },
  partial: {
    id: 'group-view-partial',
    defaultMessage:
      'Showing {shown} of {total} matches. Narrow the search to see the rest.',
  },
});

export interface MemberResultsProps {
  /** The group whose page this is. */
  groupId: string;
  /** What was searched for. Empty before anybody has searched. */
  query: string;
  /** The answer to `query`, or null while there is none yet. */
  result: GroupMembers | null;
}

const MemberResults: React.FC<MemberResultsProps> = ({
  groupId,
  query,
  result,
}) => {
  const intl = useIntl();

  if (!query) {
    return <p className="identity-note">{intl.formatMessage(messages.hint)}</p>;
  }
  if (!result) {
    return (
      <p className="identity-note" role="status">
        {intl.formatMessage(messages.searching)}
      </p>
    );
  }
  if (!result.items.length) {
    return (
      <p className="identity-note">
        {intl.formatMessage(messages.noMatch, { query })}
      </p>
    );
  }
  return (
    <div className="identity-member-results">
      <ul>
        {result.items.map((member) => (
          <MemberRow key={member.id} member={member} groupId={groupId} />
        ))}
      </ul>
      {result.items_total > result.items.length ? (
        <p className="identity-note">
          {intl.formatMessage(messages.partial, {
            shown: result.items.length,
            total: result.items_total,
          })}
        </p>
      ) : null}
    </div>
  );
};

export default MemberResults;

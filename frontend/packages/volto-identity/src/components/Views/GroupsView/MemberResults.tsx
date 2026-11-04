/**
 * A page of a group's members, searched or not.
 *
 * Every state under the search box: a status while the page is on its way,
 * a note when a search matched nobody, and the people otherwise -- a page of
 * them at a time, with Volto's pagination under the list when there is more
 * than one page.
 *
 * Given the page rather than reading it from the store, so every one of
 * those states is a set of props. Deciding which answer belongs to which
 * query is the page's job.
 * @module components/Views/GroupsView/MemberResults
 */
import React from 'react';
import { defineMessages, useIntl } from 'react-intl';

import MemberRow from './MemberRow';
import MembersPagination from './MembersPagination';
import type { GroupMembers } from '../../../types';

import './MemberResults.scss';

const messages = defineMessages({
  loading: { id: 'group-view-loading', defaultMessage: 'Loading members…' },
  searching: { id: 'group-view-searching', defaultMessage: 'Searching…' },
  noMatch: {
    id: 'group-view-no-match',
    defaultMessage: 'Nobody in this group matches “{query}”.',
  },
});

export interface MemberResultsProps {
  /** The group whose page this is. */
  groupId: string;
  /** What was searched for. Empty when nobody has searched. */
  query: string;
  /** The page of members for `query`, or null while there is none yet. */
  result: GroupMembers | null;
}

const MemberResults: React.FC<MemberResultsProps> = ({
  groupId,
  query,
  result,
}) => {
  const intl = useIntl();

  if (!result) {
    return (
      <p className="identity-note" role="status">
        {intl.formatMessage(query ? messages.searching : messages.loading)}
      </p>
    );
  }
  if (!result.items.length) {
    // Only a search can come back empty: a group with nobody in it says so
    // before there is anything to list.
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
      <MembersPagination total={result.items_total} />
    </div>
  );
};

export default MemberResults;

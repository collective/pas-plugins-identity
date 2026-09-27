/**
 * The search box on a group page, and the URL it writes to.
 *
 * The query lives in the URL, as `?q=`, so a search can be linked to and the
 * back button leaves it. The box runs ahead of the URL: what is typed is
 * written there once typing pauses, and by replacing the location rather
 * than pushing one, because every pause in typing is not somewhere the back
 * button should stop.
 *
 * `useMemberQuery` reads the same parameter, for the page that has to act on
 * it. The URL is the only place the query is kept, so the two cannot
 * disagree.
 * @module components/Views/GroupsView/MemberSearch
 */
import React, { useEffect, useState } from 'react';
import { defineMessages, useIntl } from 'react-intl';
import { useHistory, useLocation } from 'react-router-dom';
import { SearchField } from '@plone/components';

// `@plone/components` ships its CSS separately from its components, so a
// SearchField rendered without this is unstyled.
import '@plone/components/src/styles/basic/SearchField.css';

import './MemberSearch.scss';

/** The query-string parameter the search is kept in. */
export const QUERY_PARAMETER = 'q';

/** How long typing has to pause before the search is sent. */
export const SEARCH_DELAY = 300;

const messages = defineMessages({
  search: {
    id: 'group-view-search',
    defaultMessage: 'Search members',
  },
  placeholder: {
    id: 'group-view-search-placeholder',
    defaultMessage: 'Name or login',
  },
});

/**
 * Read the member search out of the URL.
 *
 * @returns The query, trimmed; empty when there is none.
 */
export function useMemberQuery(): string {
  const { search } = useLocation();
  return (new URLSearchParams(search).get(QUERY_PARAMETER) ?? '').trim();
}

const MemberSearch: React.FC = () => {
  const intl = useIntl();
  const history = useHistory();
  const { pathname } = useLocation();
  const query = useMemberQuery();
  // What is in the box, which runs ahead of the URL by the search delay.
  const [text, setText] = useState(query);

  useEffect(() => {
    const next = text.trim();
    if (next === query) {
      return undefined;
    }
    const timer = setTimeout(() => {
      history.replace({
        pathname,
        search: next ? `?${QUERY_PARAMETER}=${encodeURIComponent(next)}` : '',
      });
    }, SEARCH_DELAY);
    return () => clearTimeout(timer);
  }, [text, query, history, pathname]);

  return (
    <div className="identity-member-search">
      <SearchField
        label={intl.formatMessage(messages.search)}
        placeholder={intl.formatMessage(messages.placeholder)}
        value={text}
        onChange={setText}
      />
    </div>
  );
};

export default MemberSearch;

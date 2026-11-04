/**
 * The pages of a group's membership, and the URL they are kept in.
 *
 * Volto's own `Pagination`, the one its Contents view and its users and
 * groups control panels page with, so a long group looks like every other
 * long list in the site. The page is kept in the URL as `?page=`, counted
 * from 1, as Volto's listing and search blocks keep theirs: a page can be
 * linked to and the back button returns to the one before.
 *
 * Every other parameter is kept as it is, so paging a search stays within
 * the search. Searching again starts from the first page, because the
 * search box writes `?q=` alone -- see `MemberSearch`.
 *
 * `useMemberPage` reads the same parameter, for the page that has to load
 * it. The URL is the only place the page is kept, so the two cannot
 * disagree.
 * @module components/Views/GroupsView/MembersPagination
 */
import React from 'react';
import { defineMessages, useIntl } from 'react-intl';
import { useHistory, useLocation } from 'react-router-dom';

import VoltoPagination from '@plone/volto/components/theme/Pagination/Pagination';

import { MEMBERS_PAGE_SIZE } from '../../../actions';

import './MembersPagination.scss';

/**
 * Volto's component, with the props its `propTypes` declare.
 *
 * It is wrapped in `injectIntl`, and TypeScript, reading the JavaScript
 * source, takes the wrapper's `intl` for the props; the cast states the
 * props the component actually takes and changes nothing at runtime.
 */
const Pagination = VoltoPagination as unknown as React.ComponentType<{
  current: number;
  total: number;
  pageSize?: number;
  pageSizes?: (number | string)[];
  onChangePage: (event: React.SyntheticEvent, data: { value: number }) => void;
  onChangePageSize?: (
    event: React.SyntheticEvent,
    data: { value: number },
  ) => void;
}>;

/** The query-string parameter the page is kept in. */
export const PAGE_PARAMETER = 'page';

const messages = defineMessages({
  pages: { id: 'group-view-pages', defaultMessage: 'Pages of members' },
});

/**
 * Read the page out of the URL.
 *
 * @returns The page, counted from 1; 1 when there is none or it is not a
 *   page number.
 */
export function useMemberPage(): number {
  const { search } = useLocation();
  const page = parseInt(
    new URLSearchParams(search).get(PAGE_PARAMETER) ?? '',
    10,
  );
  return Number.isFinite(page) && page > 1 ? page : 1;
}

export interface MembersPaginationProps {
  /** How many rows there are on every page together. */
  total: number;
  /** How many rows a page holds. */
  pageSize?: number;
}

const MembersPagination: React.FC<MembersPaginationProps> = ({
  total,
  pageSize = MEMBERS_PAGE_SIZE,
}) => {
  const intl = useIntl();
  const history = useHistory();
  const { pathname, search } = useLocation();
  const page = useMemberPage();
  const pages = Math.ceil(total / pageSize);

  if (pages <= 1) {
    return null;
  }

  const onChangePage = (
    _event: React.SyntheticEvent,
    { value }: { value: number },
  ) => {
    const params = new URLSearchParams(search);
    if (value > 0) {
      params.set(PAGE_PARAMETER, String(value + 1));
    } else {
      params.delete(PAGE_PARAMETER);
    }
    const next = params.toString();
    history.push({ pathname, search: next ? `?${next}` : '' });
  };

  return (
    <nav
      className="identity-members-pagination"
      aria-label={intl.formatMessage(messages.pages)}
    >
      <Pagination
        // Volto's counts from 0; a page past the end shows the last one.
        current={Math.min(page, pages) - 1}
        total={pages}
        onChangePage={onChangePage}
      />
    </nav>
  );
};

export default MembersPagination;

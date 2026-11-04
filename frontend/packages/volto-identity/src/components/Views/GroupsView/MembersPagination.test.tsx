/**
 * Volto's pagination, kept in the URL as `?page=`.
 */
import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '../../../testing';
import React from 'react';
import { MemoryRouter, useLocation } from 'react-router-dom';

import MembersPagination, { useMemberPage } from './MembersPagination';

let location: { search: string } = { search: '' };

/** Record where the pagination sent the reader. */
const Spy = () => {
  location = useLocation();
  return <span data-testid="page">{useMemberPage()}</span>;
};

/**
 * Render the pagination at a URL.
 *
 * @param total How many rows there are.
 * @param url Where the page is open.
 */
function renderAt(total: number, url = '/identity-profiles/staff'): void {
  render(
    <MemoryRouter initialEntries={[url]}>
      <MembersPagination total={total} />
      <Spy />
    </MemoryRouter>,
  );
}

/**
 * Click a page number.
 *
 * @param label The number as it is shown.
 */
function clickPage(label: string): void {
  const nav = screen.getByRole('navigation', { name: 'Pages of members' });
  const item = [...nav.querySelectorAll('.item')].find(
    (element) => element.textContent === label,
  );
  fireEvent.click(item as Element);
}

describe('MembersPagination', () => {
  it('draws nothing when one page holds everybody', () => {
    renderAt(10);

    expect(screen.queryByRole('navigation')).toBeNull();
  });

  it('pages in tens', () => {
    renderAt(11);

    expect(screen.getByRole('navigation')).toBeTruthy();
  });

  it('starts on the first page', () => {
    renderAt(95);

    expect(screen.getByTestId('page').textContent).toBe('1');
    expect(document.querySelector('.item.active')?.textContent).toBe('1');
  });

  it('shows the page in the URL as current', () => {
    renderAt(95, '/identity-profiles/staff?page=5');

    expect(document.querySelector('.item.active')?.textContent).toBe('5');
  });

  it('writes the page chosen to the URL, counted from one', () => {
    renderAt(95);

    clickPage('2');

    expect(location.search).toBe('?page=2');
  });

  it('keeps the search when paging', () => {
    renderAt(95, '/identity-profiles/staff?q=li');

    clickPage('3');

    expect(new URLSearchParams(location.search).get('q')).toBe('li');
    expect(new URLSearchParams(location.search).get('page')).toBe('3');
  });

  it('leaves the first page out of the URL', () => {
    renderAt(95, '/identity-profiles/staff?q=li&page=2');

    clickPage('1');

    expect(location.search).toBe('?q=li');
  });

  it('shows the last page for a page past the end', () => {
    renderAt(25, '/identity-profiles/staff?page=9');

    expect(document.querySelector('.item.active')?.textContent).toBe('3');
  });

  it.each(['0', '-2', 'two'])('reads %s as the first page', (page) => {
    renderAt(95, `/identity-profiles/staff?page=${page}`);

    expect(screen.getByTestId('page').textContent).toBe('1');
  });
});

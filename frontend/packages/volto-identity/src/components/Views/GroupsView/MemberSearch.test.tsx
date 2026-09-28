import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '../../../testing';
import { MemoryRouter, Route } from 'react-router-dom';
import type { RouteComponentProps } from 'react-router-dom';
import React from 'react';

import MemberSearch, { SEARCH_DELAY, useMemberQuery } from './MemberSearch';

type History = RouteComponentProps['history'];

/**
 * Render the box at a URL, and keep hold of the router's history.
 *
 * @param url Where the page is open, `?q=` included.
 * @returns The history, read after the render.
 */
function renderSearch(url = '/identity-groups/staff'): () => History {
  let routerHistory: History | undefined;
  render(
    <MemoryRouter initialEntries={[url]}>
      <MemberSearch />
      <Route
        render={({ history }) => {
          routerHistory = history;
          return null;
        }}
      />
    </MemoryRouter>,
  );
  return () => routerHistory as History;
}

/**
 * Type into the box.
 *
 * @param value What to type.
 */
function type(value: string): void {
  fireEvent.change(screen.getByRole('searchbox'), { target: { value } });
}

afterEach(() => {
  vi.useRealTimers();
});

describe('MemberSearch', () => {
  it('is labelled', () => {
    renderSearch();

    expect(screen.getByLabelText('Search members')).toBeTruthy();
  });

  it('puts the query from the URL in the box', () => {
    renderSearch('/identity-groups/staff?q=ali');

    expect((screen.getByRole('searchbox') as HTMLInputElement).value).toBe(
      'ali',
    );
  });

  it('writes what is typed into the URL once typing pauses', () => {
    vi.useFakeTimers();
    const history = renderSearch();

    type('ali');
    act(() => {
      vi.advanceTimersByTime(SEARCH_DELAY - 1);
    });
    expect(history().location.search).toBe('');
    act(() => {
      vi.advanceTimersByTime(1);
    });

    expect(history().location.search).toBe('?q=ali');
  });

  it('keeps the page it is on', () => {
    vi.useFakeTimers();
    const history = renderSearch();

    type('ali');
    act(() => {
      vi.runAllTimers();
    });

    expect(history().location.pathname).toBe('/identity-groups/staff');
  });

  it('replaces the location rather than adding to the history', () => {
    // Every pause in typing is not somewhere the back button should stop.
    vi.useFakeTimers();
    const history = renderSearch();

    type('ali');
    act(() => {
      vi.runAllTimers();
    });

    expect(history().action).toBe('REPLACE');
    expect(history().length).toBe(1);
  });

  it('writes only what typing settled on', () => {
    vi.useFakeTimers();
    const history = renderSearch();

    type('a');
    type('al');
    type('ali');
    act(() => {
      vi.runAllTimers();
    });

    expect(history().location.search).toBe('?q=ali');
  });

  it('drops the query from the URL when the box is cleared', () => {
    vi.useFakeTimers();
    const history = renderSearch('/identity-groups/staff?q=ali');

    type('');
    act(() => {
      vi.runAllTimers();
    });

    expect(history().location.search).toBe('');
  });

  it('does not search for blank space', () => {
    vi.useFakeTimers();
    const history = renderSearch();

    type('   ');
    act(() => {
      vi.runAllTimers();
    });

    expect(history().action).not.toBe('REPLACE');
  });
});

describe('useMemberQuery', () => {
  /**
   * Render the hook's answer at a URL.
   *
   * @param url Where the page is open.
   * @returns What the hook read.
   */
  function queryAt(url: string): string {
    let value = '';
    const Probe = () => {
      value = useMemberQuery();
      return null;
    };
    render(
      <MemoryRouter initialEntries={[url]}>
        <Probe />
      </MemoryRouter>,
    );
    return value;
  }

  it('reads the query from the URL', () => {
    expect(queryAt('/identity-groups/staff?q=ali')).toBe('ali');
  });

  it('decodes it', () => {
    expect(queryAt('/identity-groups/staff?q=o%27brien')).toBe("o'brien");
  });

  it('trims it', () => {
    expect(queryAt('/identity-groups/staff?q=%20ali%20')).toBe('ali');
  });

  it('is empty when there is none', () => {
    expect(queryAt('/identity-groups/staff')).toBe('');
  });
});

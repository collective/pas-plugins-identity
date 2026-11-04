import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '../../testing';
import React from 'react';

import AddMembers, { CANDIDATE_SEARCH_DELAY } from './AddMembers';
import type { AddMembersProps, Candidate } from './AddMembers';

const DEVELOPERS: Candidate = {
  id: 'developers',
  title: 'Developers',
  type: 'group',
};
const ALICE: Candidate = {
  id: 'alice',
  title: 'Alice Liddell',
  type: 'user',
  detail: 'alice@example.com',
};
const BOB: Candidate = { id: 'bob', title: 'Bob Cratchit', type: 'user' };

/**
 * Render the form.
 *
 * @param props What this test is about.
 * @returns The callbacks, to assert on.
 */
function renderForm(props: Partial<AddMembersProps> = {}) {
  const onQuery = vi.fn();
  const onAdd = vi.fn();
  const { rerender } = render(
    <AddMembers
      query="ali"
      onQuery={onQuery}
      candidates={[DEVELOPERS, ALICE]}
      searching={false}
      busy={false}
      onAdd={onAdd}
      {...props}
    />,
  );
  return { onQuery, onAdd, rerender };
}

const addButton = () => screen.getByRole('button', { name: /^Add/ });

afterEach(() => {
  vi.useRealTimers();
});

describe('AddMembers', () => {
  it('searches once typing pauses', () => {
    vi.useFakeTimers();
    const { onQuery } = renderForm({ query: '', candidates: [] });

    fireEvent.change(screen.getByLabelText('Find people or groups'), {
      target: { value: 'bob' },
    });
    act(() => {
      vi.advanceTimersByTime(CANDIDATE_SEARCH_DELAY - 1);
    });
    expect(onQuery).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(1);
    });

    expect(onQuery).toHaveBeenCalledWith('bob');
  });

  it('lists people and groups, and says which is a group', () => {
    renderForm();

    expect(screen.getByLabelText(/^Alice Liddell/)).toBeTruthy();
    expect(
      screen.getByLabelText(/^Developers/).closest('label')?.textContent,
    ).toContain('Group');
  });

  it('adds nothing until something is picked', () => {
    renderForm();

    expect((addButton() as HTMLButtonElement).disabled).toBe(true);
  });

  it('adds everybody picked, at once', () => {
    const { onAdd } = renderForm();

    fireEvent.click(screen.getByLabelText(/^Alice Liddell/));
    fireEvent.click(screen.getByLabelText(/^Developers/));
    expect(addButton().textContent).toBe('Add 2 members');
    fireEvent.click(addButton());

    expect(onAdd).toHaveBeenCalledWith([ALICE, DEVELOPERS]);
  });

  it('keeps what was picked across searches', () => {
    // Three people found by three names, added with one request.
    const { onAdd, rerender } = renderForm();
    fireEvent.click(screen.getByLabelText(/^Alice Liddell/));

    rerender(
      <AddMembers
        query="bob"
        onQuery={() => {}}
        candidates={[BOB]}
        searching={false}
        busy={false}
        onAdd={onAdd}
      />,
    );
    fireEvent.click(screen.getByLabelText(/^Bob Cratchit/));
    fireEvent.click(addButton());

    expect(onAdd).toHaveBeenCalledWith([ALICE, BOB]);
  });

  it('lets a pick be taken back', () => {
    renderForm();
    fireEvent.click(screen.getByLabelText(/^Alice Liddell/));

    fireEvent.click(
      screen.getByRole('button', { name: 'Do not add Alice Liddell' }),
    );

    expect((addButton() as HTMLButtonElement).disabled).toBe(true);
  });

  it('clears the picks once they are added', () => {
    renderForm();
    fireEvent.click(screen.getByLabelText(/^Alice Liddell/));

    fireEvent.click(addButton());

    expect(addButton().textContent).toBe('Add');
  });

  it('says so while searching', () => {
    renderForm({ searching: true, candidates: [] });

    expect(screen.getByRole('status').textContent).toBe('Searching…');
  });

  it('says so when nobody matches', () => {
    renderForm({ query: 'zelda', candidates: [] });

    expect(screen.getByText('Nobody matches “zelda”.')).toBeTruthy();
  });

  it('offers nothing to pick while a change is saved', () => {
    renderForm({ busy: true });

    expect(
      (screen.getByLabelText(/^Alice Liddell/) as HTMLInputElement).disabled,
    ).toBe(true);
  });
});

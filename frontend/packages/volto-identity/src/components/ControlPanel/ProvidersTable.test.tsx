import { describe, expect, it, vi } from 'vitest';
import {
  dragByKeyboard,
  dragHandles,
  fireEvent,
  render,
  screen,
  within,
} from '../../testing';
import React from 'react';

import ProvidersTable from './ProvidersTable';
import { providerEditUrl } from '../../config/routes';
import { CONFIGURED } from '../../stories/fixtures';
import type { ConfiguredProvider } from '../../types';

/**
 * Render the list.
 *
 * @param providers The providers to list.
 * @param extra Further props for the list.
 * @returns The handlers the list was given.
 */
function renderTable(
  providers: ConfiguredProvider[] = CONFIGURED,
  extra: Record<string, unknown> = {},
) {
  const handlers = { onReorder: vi.fn(), onTest: vi.fn(), onDelete: vi.fn() };
  render(<ProvidersTable providers={providers} {...handlers} {...extra} />);
  return handlers;
}

/** The provider ids, in the order the rows are on the page. */
function shown(): string[] {
  return [...document.querySelectorAll<HTMLElement>('[data-provider]')].map(
    (row) => row.dataset.provider as string,
  );
}

/**
 * One row's cell under a column.
 *
 * @param providerId The row.
 * @param column The column header's text.
 * @returns The cell's text.
 */
function cell(providerId: string, column: string): string | null {
  const index = screen
    .getAllByRole('columnheader')
    .findIndex((header) => header.textContent === column);
  const row = document.querySelector(
    `[data-provider="${providerId}"]`,
  ) as HTMLElement;
  return row.querySelectorAll('td, th')[index].textContent;
}

describe('ProvidersTable', () => {
  it('lists the providers in the order given', () => {
    renderTable();

    expect(shown()).toEqual(['keycloak', 'github']);
  });

  it('says whether the login screen offers each provider', () => {
    // Enabled and shown on purpose apart, so the column cannot be reading
    // the wrong one of the two.
    renderTable([
      { ...CONFIGURED[0], enabled: true, show_in_login: false },
      { ...CONFIGURED[1], enabled: false, show_in_login: true },
    ]);

    expect(cell('keycloak', 'Enabled')).toBe('Yes');
    expect(cell('keycloak', 'Login screen')).toBe('No');
    expect(cell('github', 'Enabled')).toBe('No');
    expect(cell('github', 'Login screen')).toBe('Yes');
  });

  it("links each row to its edit form and hands on the row's actions", () => {
    const { onTest, onDelete } = renderTable();

    fireEvent.click(
      screen.getByRole('button', { name: 'Test connection to GitHub' }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Delete GitHub' }));

    expect(
      screen.getByRole('link', { name: 'Edit GitHub' }).getAttribute('href'),
    ).toBe(providerEditUrl('github'));
    expect(onTest).toHaveBeenCalledWith(CONFIGURED[1]);
    expect(onDelete).toHaveBeenCalledWith(CONFIGURED[1]);
  });

  it('names every action for the provider it acts on', () => {
    // One "Delete" per row tells a screen reader nothing about which.
    renderTable();
    const row = document.querySelector(
      '[data-provider="keycloak"]',
    ) as HTMLElement;

    expect(
      within(row).getByRole('link', { name: 'Edit Sign in with Keycloak' }),
    ).toBeTruthy();
    expect(
      within(row).getByRole('button', {
        name: 'Delete Sign in with Keycloak',
      }),
    ).toBeTruthy();
  });

  it('offers each row an export when it is given somewhere to send it', () => {
    const onExport = vi.fn();
    renderTable(CONFIGURED, { onExport });

    fireEvent.click(screen.getByRole('button', { name: 'Export GitHub' }));

    expect(onExport).toHaveBeenCalledWith(CONFIGURED[1]);
  });

  it('offers no export without one', () => {
    // Exporting needs a permission of its own, and the panel passes nothing
    // to a caller who lacks it.
    renderTable();

    expect(screen.queryByRole('button', { name: /^Export / })).toBeNull();
  });

  describe('dragging', () => {
    it('gives every row a handle named for its provider', () => {
      // From the first render: nothing is loaded lazily any more.
      renderTable();

      const handles = dragHandles();
      expect(handles).toHaveLength(2);
      expect(handles[0].getAttribute('aria-label')).toMatch(/Keycloak/);
      expect(handles[1].getAttribute('aria-label')).toMatch(/GitHub/);
    });

    it('moves a row up from the keyboard', async () => {
      const { onReorder } = renderTable();

      await dragByKeyboard(dragHandles()[1], ['ArrowUp']);

      expect(onReorder).toHaveBeenCalledWith(['github', 'keycloak']);
    });

    it('moves a row down from the keyboard', async () => {
      const { onReorder } = renderTable();

      await dragByKeyboard(dragHandles()[0], ['ArrowDown']);

      expect(onReorder).toHaveBeenCalledWith(['github', 'keycloak']);
    });

    it('reports nothing for a row dropped where it started', async () => {
      // Nothing to save, so the panel sends no request.
      const { onReorder } = renderTable();

      await dragByKeyboard(dragHandles()[1], ['ArrowUp', 'ArrowDown']);

      expect(onReorder).not.toHaveBeenCalled();
    });
  });
});

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, within } from '../../testing';
import { Provider } from 'react-redux';
import React from 'react';

import ProvidersTable, { DND_LIBRARIES } from './ProvidersTable';
import { providerEditUrl } from '../../config/routes';
import { CONFIGURED, loadLazyLibraries } from '../../stories/fixtures';
import type { ConfiguredProvider } from '../../types';

let libraries: Record<string, any>;

beforeAll(async () => {
  libraries = await loadLazyLibraries(DND_LIBRARIES);
});

afterEach(() => {
  vi.restoreAllMocks();
});

/**
 * Render the list over a store holding the given lazy libraries.
 *
 * @param lazyLibraries The `lazyLibraries` slice; empty is the state before
 *   the drag library has loaded.
 * @param providers The providers to list.
 * @param extra Further props for the list.
 * @returns The handlers the list was given.
 */
function renderTable(
  lazyLibraries: Record<string, unknown> = libraries,
  providers: ConfiguredProvider[] = CONFIGURED,
  extra: Record<string, unknown> = {},
) {
  const handlers = { onReorder: vi.fn(), onTest: vi.fn(), onDelete: vi.fn() };
  const state = { lazyLibraries };
  const store = {
    getState: () => state,
    dispatch: (action: unknown) => action,
    subscribe: () => () => {},
  };
  render(
    <Provider store={store as any}>
      <ProvidersTable providers={providers} {...handlers} {...extra} />
    </Provider>,
  );
  return handlers;
}

/**
 * The drag library, keeping the drop handler the list gives it.
 *
 * @returns The libraries, and where the handler is kept.
 */
function keepingTheDrop() {
  const drop: { end?: (event: unknown) => void } = {};
  const Real = libraries.dndKitCore.DndContext;
  const DndContext = (props: any) => {
    drop.end = props.onDragEnd;
    return <Real {...props} />;
  };
  return {
    drop,
    lazyLibraries: {
      ...libraries,
      dndKitCore: { ...libraries.dndKitCore, DndContext },
    },
  };
}

/** The provider ids, in the order the rows are on the page. */
function shown(): string[] {
  return [...document.querySelectorAll<HTMLElement>('tr[data-provider]')].map(
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
    `tr[data-provider="${providerId}"]`,
  ) as HTMLTableRowElement;
  return row.cells[index].textContent;
}

describe('ProvidersTable', () => {
  it('lists the providers in the order given', () => {
    renderTable();

    expect(shown()).toEqual(['keycloak', 'github']);
  });

  it('says whether the login screen offers each provider', () => {
    // Enabled and shown on purpose apart, so the column cannot be reading
    // the wrong one of the two.
    renderTable(libraries, [
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
    const row = document.querySelector(
      'tr[data-provider="github"]',
    ) as HTMLElement;

    fireEvent.click(
      within(row).getByRole('button', { name: 'Test connection' }),
    );
    fireEvent.click(within(row).getByRole('button', { name: 'Delete' }));

    // Semantic's Button gives the anchor it renders the role of a button.
    expect(
      within(row).getByRole('button', { name: 'Edit' }).getAttribute('href'),
    ).toBe(providerEditUrl('github'));
    expect(onTest).toHaveBeenCalledWith(CONFIGURED[1]);
    expect(onDelete).toHaveBeenCalledWith(CONFIGURED[1]);
  });

  it('offers each row an export when it is given somewhere to send it', () => {
    const onExport = vi.fn();
    renderTable(libraries, CONFIGURED, { onExport });
    const row = document.querySelector(
      'tr[data-provider="github"]',
    ) as HTMLElement;

    fireEvent.click(within(row).getByRole('button', { name: 'Export' }));

    expect(onExport).toHaveBeenCalledWith(CONFIGURED[1]);
  });

  it('offers no export without one', () => {
    // Exporting needs a permission of its own, and the panel passes nothing
    // to a caller who lacks it.
    renderTable();

    expect(screen.queryByRole('button', { name: 'Export' })).toBeNull();
  });

  describe('before the drag library has loaded', () => {
    it('lists the providers without handles', () => {
      // On the server, and for a moment on the client: the list does not
      // wait for a library only the handles need.
      renderTable({});

      expect(shown()).toEqual(['keycloak', 'github']);
      expect(screen.queryByRole('button', { name: /^Move / })).toBeNull();
    });
  });

  describe('once the drag library has loaded', () => {
    it('gives every row a handle', () => {
      renderTable();

      const handle = screen.getByRole('button', { name: 'Move GitHub' });
      expect(handle.getAttribute('aria-roledescription')).toBe('sortable');
      expect(
        screen.getByRole('button', { name: 'Move Sign in with Keycloak' }),
      ).toBeTruthy();
    });

    it("reports the new order when a row is dropped in another's place", () => {
      const { drop, lazyLibraries } = keepingTheDrop();
      const { onReorder } = renderTable(lazyLibraries);

      act(() =>
        drop.end!({ active: { id: 'github' }, over: { id: 'keycloak' } }),
      );

      expect(onReorder).toHaveBeenCalledWith(['github', 'keycloak']);
    });

    it('reports nothing for a row dropped where it started', () => {
      const { drop, lazyLibraries } = keepingTheDrop();
      const { onReorder } = renderTable(lazyLibraries);

      act(() =>
        drop.end!({ active: { id: 'github' }, over: { id: 'github' } }),
      );
      act(() => drop.end!({ active: { id: 'github' }, over: null }));

      expect(onReorder).not.toHaveBeenCalled();
    });

    it('moves a row from the keyboard', async () => {
      // jsdom lays nothing out, so each row is given the box it would have:
      // the keyboard moves a row to the neighbour it finds by position.
      vi.spyOn(
        HTMLElement.prototype,
        'getBoundingClientRect',
      ).mockImplementation(function (this: HTMLElement) {
        const row = this.closest<HTMLElement>('tr[data-provider]');
        const top = row ? shown().indexOf(row.dataset.provider!) * 40 : 0;
        return {
          x: 0,
          y: top,
          top,
          left: 0,
          right: 600,
          bottom: top + 40,
          width: 600,
          height: 40,
          toJSON: () => ({}),
        } as DOMRect;
      });
      const tick = () =>
        act(() => new Promise((resolve) => setTimeout(resolve, 0)));
      const { onReorder } = renderTable();
      const handle = screen.getByRole('button', { name: 'Move GitHub' });

      handle.focus();
      fireEvent.keyDown(handle, { code: 'Space' });
      await tick();
      fireEvent.keyDown(document, { code: 'ArrowUp' });
      await tick();
      fireEvent.keyDown(document, { code: 'Space' });
      await tick();

      expect(onReorder).toHaveBeenCalledWith(['github', 'keycloak']);
    });
  });
});

import {
  afterAll,
  afterEach,
  beforeAll,
  describe,
  expect,
  it,
  vi,
} from 'vitest';
import { act, fireEvent, render, screen, within } from '../../../testing';
import { Provider } from 'react-redux';
import React from 'react';

import config from '@plone/volto/registry';

import OrderedListTable from './OrderedListTable';
import { DND_LIBRARIES } from '../../ControlPanel/ProvidersTable';
import { loadLazyLibraries } from '../../../stories/fixtures';
import type { ItemSchema, Row } from '../../../helpers/orderedList';

let libraries: Record<string, any>;
let widgets: any;

/**
 * A text input, standing in for every widget the dialog renders.
 *
 * The test configuration's widgets are placeholders that render a label and
 * no input, so there would be nothing to type into.
 */
const TextWidget = ({ id, title, value, onChange }: any) => (
  <label>
    {title}
    <input
      value={value ?? ''}
      onChange={(event) => onChange(id, event.target.value)}
    />
  </label>
);

beforeAll(async () => {
  libraries = await loadLazyLibraries(DND_LIBRARIES);
  widgets = config.widgets;
  config.set('widgets', { ...widgets, default: TextWidget });
});

afterAll(() => {
  config.set('widgets', widgets);
});

afterEach(() => {
  vi.restoreAllMocks();
});

const SCHEMA: ItemSchema = {
  title: 'Link',
  fieldsets: [
    { id: 'default', title: 'Default', fields: ['id', 'title', 'href'] },
  ],
  properties: {
    id: {
      title: 'Network',
      choices: [
        ['github', 'GitHub'],
        ['mastodon', 'Mastodon'],
      ],
    },
    title: { title: 'Title' },
    href: { title: 'Target' },
  },
  required: ['title'],
};

const ROWS: Row[] = [
  {
    '@id': 'a',
    id: 'github',
    title: 'Code',
    href: [{ '@id': 'https://github.com/ericof', title: 'github.com/ericof' }],
  },
  {
    '@id': 'b',
    id: 'mastodon',
    title: 'Toots',
    href: [{ '@id': 'https://plone.social/@ericof' }],
  },
];

/**
 * Render the table inside a form, over a store holding the lazy libraries.
 *
 * @param props Props to replace.
 * @param lazyLibraries The `lazyLibraries` slice; empty is the state before
 *   the drag library has loaded.
 * @returns The handlers: what the table reports, and what the enclosing
 *   content form would have been asked to save.
 */
function renderTable(
  props: Record<string, unknown> = {},
  lazyLibraries: Record<string, unknown> = libraries,
) {
  const onChangeRows = vi.fn();
  const submitted = vi.fn((event: React.FormEvent) => event.preventDefault());
  const state = { lazyLibraries };
  const store = {
    getState: () => state,
    dispatch: (action: unknown) => action,
    subscribe: () => () => {},
  };
  render(
    <Provider store={store as any}>
      <form aria-label="Content" onSubmit={submitted}>
        <OrderedListTable
          id="social_links"
          title="Profiles"
          rows={ROWS}
          schema={SCHEMA}
          columns={['id', 'title', 'href']}
          onChangeRows={onChangeRows}
          {...props}
        />
      </form>
    </Provider>,
  );
  return { onChangeRows, submitted };
}

/** The row keys, in the order the rows are on the page. */
function shown(): string[] {
  return [...document.querySelectorAll<HTMLElement>('tr[data-row]')].map(
    (row) => row.dataset.row as string,
  );
}

/** One row, by key. */
function row(key: string): HTMLElement {
  return document.querySelector(`tr[data-row="${key}"]`) as HTMLElement;
}

/** The open dialog's form. */
function dialog(): HTMLElement {
  return document.querySelector('.ui.modal form') as HTMLElement;
}

/**
 * The drag library, keeping the drop handler the table gives it.
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

describe('OrderedListTable', () => {
  it("labels the field with the field's title", () => {
    // `FormFieldWrapper` has a `columns` prop of its own -- a layout width,
    // where anything but 2 drops the label column -- so the table's columns
    // must not reach it.
    renderTable();

    expect(
      document.querySelector(
        'label#fieldset-undefined-field-label-social_links',
      )?.textContent,
    ).toBe('Profiles');
  });

  it("heads each column with its field's title", () => {
    renderTable();

    expect(
      screen.getAllByRole('columnheader').map((header) => header.textContent),
    ).toEqual(['', 'Network', 'Title', 'Target', 'Actions']);
  });

  it('shows only the columns it is given', () => {
    renderTable({ columns: ['id', 'title'] });

    expect(screen.queryByRole('columnheader', { name: 'Target' })).toBeNull();
  });

  it('shows the entries in order, a choice by its label and a link by its title', () => {
    renderTable();

    expect(shown()).toEqual(['a', 'b']);
    expect(
      [...(row('a') as HTMLTableRowElement).cells].map(
        (cell) => cell.textContent,
      ),
    ).toEqual(['', 'GitHub', 'Code', 'github.com/ericof', '']);
  });

  it('says so when there is nothing on the list', () => {
    renderTable({ rows: [] });

    expect(screen.getByText('Nothing has been added yet.')).toBeTruthy();
  });

  it('adds an entry from the dialog', async () => {
    const { onChangeRows } = renderTable();

    fireEvent.click(screen.getByRole('button', { name: 'Add Link' }));
    fireEvent.change(await within(dialog()).findByLabelText('Title'), {
      target: { value: 'Blog' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    const [rows] = onChangeRows.mock.calls[0];
    expect(rows).toHaveLength(3);
    expect(rows.slice(0, 2)).toEqual(ROWS);
    expect(rows[2].title).toBe('Blog');
    expect(document.querySelector('.ui.modal')).toBeNull();
  });

  it('edits an entry in place', async () => {
    const { onChangeRows } = renderTable();

    fireEvent.click(within(row('b')).getByRole('button', { name: 'Edit' }));
    const title = (await within(dialog()).findByLabelText(
      'Title',
    )) as HTMLInputElement;
    expect(title.value).toBe('Toots');
    fireEvent.change(title, { target: { value: 'Posts' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    expect(onChangeRows).toHaveBeenCalledWith([
      ROWS[0],
      { ...ROWS[1], title: 'Posts' },
    ]);
  });

  it('opens a new entry empty, whatever was edited before', async () => {
    // `ModalForm` keeps what it was given in state, so a dialog reused
    // across entries would carry the last one's fields into the next.
    renderTable();

    fireEvent.click(within(row('b')).getByRole('button', { name: 'Edit' }));
    await within(dialog()).findByLabelText('Title');
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add Link' }));

    expect(
      ((await within(dialog()).findByLabelText('Title')) as HTMLInputElement)
        .value,
    ).toBe('');
  });

  it('stores nothing and says why when the entry is refused', () => {
    const { onChangeRows } = renderTable({ validate: () => 'Not that one.' });

    fireEvent.click(within(row('a')).getByRole('button', { name: 'Edit' }));
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    expect(onChangeRows).not.toHaveBeenCalled();
    expect(screen.getByText('Not that one.')).toBeTruthy();
  });

  it('asks before deleting, naming the entry, and deletes on confirm', () => {
    const { onChangeRows } = renderTable();

    fireEvent.click(within(row('a')).getByRole('button', { name: 'Delete' }));

    expect(onChangeRows).not.toHaveBeenCalled();
    expect(document.querySelector('.ui.modal .header')?.textContent).toBe(
      'GitHub',
    );
    fireEvent.click(
      document.querySelector('[data-action="confirm"]') as HTMLElement,
    );

    expect(onChangeRows).toHaveBeenCalledWith([ROWS[1]]);
  });

  it('keeps the entry when the question is cancelled', () => {
    const { onChangeRows } = renderTable();

    fireEvent.click(within(row('a')).getByRole('button', { name: 'Delete' }));
    fireEvent.click(
      document.querySelector('[data-action="cancel"]') as HTMLElement,
    );

    expect(onChangeRows).not.toHaveBeenCalled();
  });

  describe('inside the content form', () => {
    it('submits nothing from its own buttons', () => {
      // A button's default type is submit, and these sit inside the form.
      const { submitted } = renderTable();

      fireEvent.click(within(row('a')).getByRole('button', { name: 'Edit' }));
      fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
      fireEvent.click(within(row('a')).getByRole('button', { name: 'Delete' }));
      fireEvent.click(
        document.querySelector('[data-action="cancel"]') as HTMLElement,
      );
      fireEvent.click(screen.getByRole('button', { name: 'Add Link' }));

      expect(submitted).not.toHaveBeenCalled();
    });

    it("does not submit the content form when the dialog's form is submitted", () => {
      // What pressing Enter in a dialog field does. The dialog renders into
      // a portal, and React hands a portal's submit to its React ancestors.
      const { onChangeRows, submitted } = renderTable();

      fireEvent.click(within(row('a')).getByRole('button', { name: 'Edit' }));
      fireEvent.submit(dialog());

      expect(onChangeRows).toHaveBeenCalled();
      expect(submitted).not.toHaveBeenCalled();
    });
  });

  describe('before the drag library has loaded', () => {
    it('lists the entries without handles', () => {
      renderTable({}, {});

      expect(shown()).toEqual(['a', 'b']);
      expect(screen.queryByRole('button', { name: /^Move / })).toBeNull();
    });
  });

  describe('once the drag library has loaded', () => {
    it('gives every row a handle named for its entry', () => {
      renderTable();

      expect(screen.getByRole('button', { name: 'Move GitHub' })).toBeTruthy();
      expect(
        screen.getByRole('button', { name: 'Move Mastodon' }),
      ).toBeTruthy();
    });

    it("reports the new order when a row is dropped in another's place", () => {
      const { drop, lazyLibraries } = keepingTheDrop();
      const { onChangeRows } = renderTable({}, lazyLibraries);

      act(() => drop.end!({ active: { id: 'b' }, over: { id: 'a' } }));

      expect(onChangeRows).toHaveBeenCalledWith([ROWS[1], ROWS[0]]);
    });

    it('reports nothing for a row dropped where it started', () => {
      const { drop, lazyLibraries } = keepingTheDrop();
      const { onChangeRows } = renderTable({}, lazyLibraries);

      act(() => drop.end!({ active: { id: 'b' }, over: { id: 'b' } }));
      act(() => drop.end!({ active: { id: 'b' }, over: null }));

      expect(onChangeRows).not.toHaveBeenCalled();
    });
  });

  describe('disabled', () => {
    it('offers no handle and no action', () => {
      renderTable({ isDisabled: true });

      expect(screen.queryByRole('button', { name: /^Move / })).toBeNull();
      for (const button of screen.getAllByRole('button')) {
        expect((button as HTMLButtonElement).disabled).toBe(true);
      }
    });
  });
});

import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '../../../testing';
import { Provider } from 'react-redux';
import React from 'react';

import config from '@plone/volto/registry';

import OrderedObjectListWidget, { columnsOf } from './OrderedObjectListWidget';
import { SOCIAL_LINK_SCHEMA, SOCIAL_LINKS } from '../../../stories/fixtures';

let widgets: any;

/** A text input, standing in for every widget the dialog renders. */
const TextWidget = ({ id, title, value, onChange }: any) => (
  <label>
    {title}
    <input
      value={value ?? ''}
      onChange={(event) => onChange(id, event.target.value)}
    />
  </label>
);

beforeAll(() => {
  widgets = config.widgets;
  config.set('widgets', { ...widgets, default: TextWidget });
});

afterAll(() => {
  config.set('widgets', widgets);
});

/**
 * Render a widget over a store with no drag library loaded.
 *
 * @param props Props to replace.
 * @param Widget The widget to render.
 * @returns What the widget reported.
 */
function renderWidget(
  props: Record<string, unknown> = {},
  Widget: React.FC<any> = OrderedObjectListWidget,
) {
  const onChange = vi.fn();
  const state = { lazyLibraries: {} };
  const store = {
    getState: () => state,
    dispatch: (action: unknown) => action,
    subscribe: () => () => {},
  };
  render(
    <Provider store={store as any}>
      <Widget
        id="social_links"
        title="Profiles"
        value={SOCIAL_LINKS}
        schema={SOCIAL_LINK_SCHEMA}
        onChange={onChange}
        {...props}
      />
    </Provider>,
  );
  return onChange;
}

/** The column headers' text, handle and actions columns included. */
function headers(): (string | null)[] {
  return screen
    .getAllByRole('columnheader')
    .map((header) => header.textContent);
}

describe('columnsOf', () => {
  it('is every field when no columns are asked for', () => {
    expect(columnsOf(SOCIAL_LINK_SCHEMA)).toEqual(['id', 'title', 'href']);
    expect(columnsOf(SOCIAL_LINK_SCHEMA, [])).toEqual(['id', 'title', 'href']);
  });

  it('is the columns asked for, in their order', () => {
    expect(columnsOf(SOCIAL_LINK_SCHEMA, ['title', 'id'])).toEqual([
      'title',
      'id',
    ]);
  });
});

describe('OrderedObjectListWidget', () => {
  it('shows every field as a column by default', () => {
    renderWidget();

    expect(headers()).toEqual(['', 'Network', 'Title', 'Target', 'Actions']);
  });

  it('shows the columns a backend asks for', () => {
    renderWidget({ columns: ['title'] });

    expect(headers()).toEqual(['', 'Title', 'Actions']);
  });

  it('builds the item schema from a registered utility, given props and intl', () => {
    // How `volto-social-media`'s `socialMedia` utility is written: it reads
    // `intl` off its one argument.
    const method = vi.fn(({ intl }: any) => ({
      ...SOCIAL_LINK_SCHEMA,
      properties: {
        ...SOCIAL_LINK_SCHEMA.properties,
        title: {
          title: intl.formatMessage({ id: 'Name', defaultMessage: 'Name' }),
        },
      },
    }));
    config.registerUtility({ name: 'testLinks', type: 'schema', method });

    renderWidget({ schema: undefined, schemaName: 'testLinks' });

    expect(headers()).toEqual(['', 'Network', 'Name', 'Target', 'Actions']);
    expect(method.mock.calls[0][0].props.id).toBe('social_links');
  });

  it('shows its rows rather than failing when no schema has fields', () => {
    renderWidget({ schema: { type: 'array', items: { type: 'object' } } });

    expect(headers()).toEqual(['', 'Actions']);
    expect(document.querySelectorAll('tr[data-row]')).toHaveLength(2);
  });

  it('gives a new entry an @id and keeps the others', async () => {
    // Only the title required: the network and target widgets are the test
    // configuration's placeholders, which have nothing to type into.
    const onChange = renderWidget({
      schema: { ...SOCIAL_LINK_SCHEMA, required: ['title'] },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Add Link' }));
    const form = document.querySelector('.ui.modal form') as HTMLElement;
    fireEvent.change(await within(form).findByLabelText('Title'), {
      target: { value: 'Blog' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    const [id, value] = onChange.mock.calls[0];
    expect(id).toBe('social_links');
    expect(value.slice(0, 2)).toEqual(SOCIAL_LINKS);
    expect(value[2].title).toBe('Blog');
    expect(value[2]['@id']).toMatch(/^[0-9a-f-]{36}$/);
  });
});

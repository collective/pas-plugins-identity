import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '../../../testing';
import { Provider } from 'react-redux';
import React from 'react';

import config from '@plone/volto/registry';

import OrderedStringListWidget, {
  stringItemSchema,
} from './OrderedStringListWidget';
import { EMAIL_ITEMS } from '../../../stories/fixtures';

let widgets: any;

/** A text input, for the `email` widget the dialog asks for. */
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
  config.set('widgets', {
    ...widgets,
    widget: { ...widgets.widget, email: TextWidget },
  });
});

afterAll(() => {
  config.set('widgets', widgets);
});

const ITEMS = EMAIL_ITEMS;

const ADDRESSES = ['erico@plone.org', 'erico@example.com'];

/**
 * Render the widget over a store with no drag library loaded.
 *
 * @param props Props to replace.
 * @returns What the widget reported.
 */
function renderWidget(props: Record<string, unknown> = {}) {
  const onChange = vi.fn();
  const state = { lazyLibraries: {} };
  const store = {
    getState: () => state,
    dispatch: (action: unknown) => action,
    subscribe: () => () => {},
  };
  render(
    <Provider store={store as any}>
      <OrderedStringListWidget
        id="emails"
        title="Email addresses"
        value={ADDRESSES}
        items={ITEMS}
        uniqueItems
        onChange={onChange}
        {...props}
      />
    </Provider>,
  );
  return onChange;
}

/**
 * The open dialog's address field.
 *
 * Found rather than got: the `Field` Volto's `ModalForm` renders is a lazily
 * loaded component, so the input arrives a tick after the dialog does.
 */
function address(): Promise<HTMLElement> {
  const form = document.querySelector('.ui.modal form') as HTMLElement;
  return within(form).findByLabelText('Email');
}

describe('stringItemSchema', () => {
  it("carries the value type as the entry's one required field", () => {
    const schema = stringItemSchema('Email addresses', ITEMS);

    expect(schema.title).toBe('Email');
    expect(schema.required).toEqual(['value']);
    expect(schema.properties.value).toEqual(ITEMS);
  });

  it('is titled after the field when the value type has no title', () => {
    const schema = stringItemSchema('Tags', { type: 'string' });

    expect(schema.title).toBe('Tags');
    expect(schema.properties.value.title).toBe('Tags');
  });
});

describe('OrderedStringListWidget', () => {
  it("heads its one column with the value type's title", () => {
    renderWidget();

    expect(
      screen.getAllByRole('columnheader').map((header) => header.textContent),
    ).toEqual(['', 'Email', 'Actions']);
  });

  it('lists the entries in order', () => {
    renderWidget();

    expect(
      [...document.querySelectorAll('tr[data-row]')].map(
        (row) => (row as HTMLTableRowElement).cells[1].textContent,
      ),
    ).toEqual(ADDRESSES);
  });

  it('is empty rather than broken without a value', () => {
    renderWidget({ value: null });

    expect(screen.getByText('Nothing has been added yet.')).toBeTruthy();
  });

  it('asks for a new entry with the value type, and reports strings', async () => {
    const onChange = renderWidget();

    fireEvent.click(screen.getByRole('button', { name: 'Add Email' }));
    fireEvent.change(await address(), {
      target: { value: 'erico@simples.com.br' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    expect(onChange).toHaveBeenCalledWith('emails', [
      ...ADDRESSES,
      'erico@simples.com.br',
    ]);
  });

  it('refuses an entry already on the list', async () => {
    const onChange = renderWidget();

    fireEvent.click(screen.getByRole('button', { name: 'Add Email' }));
    fireEvent.change(await address(), {
      target: { value: 'erico@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    expect(onChange).not.toHaveBeenCalled();
    expect(
      screen.getByText('erico@example.com is already on the list.'),
    ).toBeTruthy();
  });

  it('lets an entry be saved unchanged', () => {
    // It is on the list -- as itself, which is no reason to refuse it.
    const onChange = renderWidget();

    fireEvent.click(
      within(
        document.querySelector('tr[data-row="#1"]') as HTMLElement,
      ).getByRole('button', { name: 'Edit' }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    expect(onChange).toHaveBeenCalledWith('emails', ADDRESSES);
  });

  it('accepts a repeated entry on a list that allows one', async () => {
    const onChange = renderWidget({ uniqueItems: false });

    fireEvent.click(screen.getByRole('button', { name: 'Add Email' }));
    fireEvent.change(await address(), {
      target: { value: 'erico@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    expect(onChange).toHaveBeenCalledWith('emails', [
      ...ADDRESSES,
      'erico@example.com',
    ]);
  });
});

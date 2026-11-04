import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '../../../testing';
import { Provider } from 'react-redux';
import React from 'react';

import config from '@plone/volto/registry';

import OrderedStringListWidget, {
  comparable,
  isEmailType,
  storedValues,
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
 * Render the widget over an empty store.
 *
 * @param props Props to replace.
 * @returns What the widget reported.
 */
function renderWidget(props: Record<string, unknown> = {}) {
  const onChange = vi.fn();
  const state = {};
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
      [...document.querySelectorAll('[data-row]')].map(
        (row) => row.querySelectorAll('td, th')[1].textContent,
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
      screen.getByRole('button', { name: 'Edit erico@example.com' }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    expect(onChange).toHaveBeenCalledWith('emails', ADDRESSES);
  });

  it('refuses an address that differs only in case', async () => {
    // The backend stores every address trimmed and lowercased, and would
    // fold this one into the existing entry without a word.
    const onChange = renderWidget();

    fireEvent.click(screen.getByRole('button', { name: 'Add Email' }));
    fireEvent.change(await address(), {
      target: { value: 'Erico@Example.COM' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    expect(onChange).not.toHaveBeenCalled();
    expect(
      screen.getByText('Erico@Example.COM is already on the list.'),
    ).toBeTruthy();
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

describe('comparable', () => {
  it('folds case for an address', () => {
    expect(comparable(' Erico@Plone.ORG ', true)).toBe('erico@plone.org');
  });

  it('keeps case for any other text', () => {
    expect(comparable(' Plone ', false)).toBe('Plone');
  });
});

describe('isEmailType', () => {
  it('knows an Email value type by its widget or its factory', () => {
    expect(isEmailType(EMAIL_ITEMS)).toBe(true);
    expect(isEmailType({ factory: 'Email' })).toBe(true);
    expect(isEmailType({ type: 'string' })).toBe(false);
    expect(isEmailType()).toBe(false);
  });
});

describe('storedValues', () => {
  it('trims every entry', () => {
    expect(storedValues([{ value: ' a ' }, { value: 'b' }])).toEqual([
      'a',
      'b',
    ]);
  });

  it('leaves out an empty entry rather than storing "undefined"', () => {
    expect(storedValues([{}, { value: '' }, { value: 'b' }])).toEqual(['b']);
  });
});

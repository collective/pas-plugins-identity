import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { IntlProvider } from 'react-intl';
import { Provider } from 'react-redux';
import React from 'react';

import PropertyMapField, { rowSchema } from './PropertyMapField';
import { toRows } from '../../helpers/propertymap';
import { USER_FIELDS_VOCABULARY } from '../../constants/vocabularies';

/**
 * react-intl 3.x predates React 18's typing of `children`, so its
 * `IntlProvider` is not assignable as written. The component works; only
 * the declaration is behind.
 */
const Intl = IntlProvider as unknown as React.FC<{
  locale: string;
  children: React.ReactNode;
}>;

describe('rowSchema', () => {
  it('takes the user field from the vocabulary', () => {
    // The whole point of the backend vocabulary: the list of fields is the
    // site's own member schema, not something enumerated here.
    expect(rowSchema().properties.field.vocabulary).toEqual({
      '@id': USER_FIELDS_VOCABULARY,
    });
  });

  it('leaves the claim as free text', () => {
    // Claim names come from the provider, so no vocabulary can know them.
    expect(rowSchema().properties.claim.vocabulary).toBeUndefined();
  });

  it('requires both halves of a row', () => {
    expect(rowSchema().required).toEqual(['claim', 'field']);
  });
});

/**
 * A store holding one loaded vocabulary, which is what the user-field
 * select reads. Same shape as the other tests here: the real store is a
 * dependency of Volto, not of this package.
 */
function fakeStore() {
  const state = {
    vocabularies: {
      [USER_FIELDS_VOCABULARY]: {
        loaded: true,
        loading: false,
        items: [
          { value: 'fullname', label: 'Full Name' },
          { value: 'home_page', label: 'Home page' },
        ],
        itemsTotal: 2,
      },
    },
    intl: { locale: 'en', messages: {} },
  };
  const dispatched: any[] = [];
  return {
    dispatched,
    store: {
      getState: () => state,
      dispatch: (action: any) => {
        dispatched.push(action);
        return action;
      },
      subscribe: () => () => {},
    },
  };
}

describe('PropertyMapField', () => {
  it('renders the stored map as rows', () => {
    // ObjectListWidget is a Volto form widget: it needs the intl context
    // and the store the control panel gives it in the real app.
    const { store } = fakeStore();
    render(
      <Provider store={store as any}>
        <Intl locale="en">
          <PropertyMapField
            id="propertymap"
            rows={toRows({ login: 'username' })}
            onChange={vi.fn()}
          />
        </Intl>
      </Provider>,
    );

    expect(screen.getByText('Attribute mapping')).toBeTruthy();
    expect(screen.getAllByRole('button', { name: /Mapping/ }).length).toBe(1);
    // ObjectListWidget renders its rows through DragDropList, which draws
    // nothing under jsdom -- so the row *contents* cannot be asserted here.
    // What can be: the widget renders a hidden "Empty object list" input
    // only when it received no rows, so its absence proves they arrived.
    expect(screen.queryByDisplayValue('Empty object list')).toBeNull();
  });

  it('reports an empty map as empty', () => {
    const { store } = fakeStore();
    render(
      <Provider store={store as any}>
        <Intl locale="en">
          <PropertyMapField id="propertymap" rows={[]} onChange={vi.fn()} />
        </Intl>
      </Provider>,
    );

    expect(screen.getByDisplayValue('Empty object list')).toBeTruthy();
  });
});

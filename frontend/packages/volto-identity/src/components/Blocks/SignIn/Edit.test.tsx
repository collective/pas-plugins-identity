import { beforeEach, describe, expect, it, vi } from 'vitest';
import React from 'react';
import { render, screen } from '../../../testing';

/**
 * What the edit component handed to the parts it is made of.
 *
 * The sidebar form is Volto's, loaded lazily and rendered into a portal the
 * editor provides; the view has its own tests. What is this component's own
 * is what it passes each of them.
 */
const { captured } = vi.hoisted(() => ({
  captured: { form: null as any, view: null as any },
}));

vi.mock('@plone/volto/components/manage/Sidebar/SidebarPortal', () => ({
  default: ({ children, selected }: any) =>
    selected ? <div data-testid="sidebar">{children}</div> : null,
}));

vi.mock('@plone/volto/components/manage/Form', () => ({
  BlockDataForm: (props: any) => {
    captured.form = props;
    return <div data-testid="block-data-form" />;
  },
}));

vi.mock('./View', () => ({
  default: (props: any) => {
    captured.view = props;
    return <div data-testid="view" />;
  },
}));

const { default: Edit } = await import('./Edit');

const DATA = { '@type': 'identitySignIn', showEmail: true };

/**
 * Render the edit component as the editor does.
 *
 * @param selected Whether the block is the selected one.
 * @returns The `onChangeBlock` spy.
 */
function renderEdit(selected = true) {
  const onChangeBlock = vi.fn();
  const props = { data: DATA, block: 'sign-in', onChangeBlock, selected };
  render(<Edit {...(props as any)} />);
  return onChangeBlock;
}

describe('Edit', () => {
  beforeEach(() => {
    captured.form = null;
    captured.view = null;
  });

  it('renders the view, told it is in the editor', () => {
    // So the preview switch means something there and nowhere else.
    renderEdit();

    expect(captured.view.isEditMode).toBe(true);
    expect(captured.view.data).toBe(DATA);
  });

  it('offers the settings only for the selected block', () => {
    renderEdit(false);

    expect(screen.queryByTestId('sidebar')).toBeNull();
  });

  it('writes a changed field into the block', () => {
    const onChangeBlock = renderEdit();

    captured.form.onChangeField('showEmail', false);

    expect(onChangeBlock).toHaveBeenCalledWith('sign-in', {
      ...DATA,
      showEmail: false,
    });
  });

  it('describes every setting the block reads', () => {
    renderEdit();

    expect(Object.keys(captured.form.schema.properties)).toEqual([
      'greeting',
      'showProfile',
      'showEmail',
      'showProvider',
      'showLastLogin',
      'previewAnonymous',
    ]);
    expect(captured.form.formData).toBe(DATA);
    expect(captured.form.block).toBe('sign-in');
  });
});

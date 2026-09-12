/**
 * The sign-in block in the editor: the view, and its sidebar.
 * @module components/Blocks/SignIn/Edit
 */
import React, { useCallback, useMemo } from 'react';
import { useIntl } from 'react-intl';
import type { BlockEditProps } from '@plone/types';
import SidebarPortal from '@plone/volto/components/manage/Sidebar/SidebarPortal';
import { BlockDataForm } from '@plone/volto/components/manage/Form';

import { signInBlockSchema } from './schema';
import View from './View';

const Edit: React.FC<BlockEditProps> = ({
  data,
  block,
  onChangeBlock,
  selected,
  blocksConfig,
  navRoot,
  contentType,
}) => {
  const intl = useIntl();
  const schema = useMemo(() => signInBlockSchema({ intl }), [intl]);
  const onChangeField = useCallback(
    (id: string, value: unknown) =>
      onChangeBlock(block, { ...data, [id]: value }),
    [block, data, onChangeBlock],
  );

  return (
    <>
      <View data={data} isEditMode />
      <SidebarPortal selected={selected}>
        <BlockDataForm
          schema={schema}
          title={schema.title}
          onChangeField={onChangeField}
          onChangeBlock={onChangeBlock}
          formData={data}
          block={block}
          blocksConfig={blocksConfig}
          navRoot={navRoot}
          contentType={contentType}
        />
      </SidebarPortal>
    </>
  );
};

export default Edit;

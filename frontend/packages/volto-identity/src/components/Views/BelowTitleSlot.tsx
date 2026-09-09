/**
 * The `belowTitle` slot, rendered by both of this package's views.
 *
 * `aboveContent` and `belowContent` need nothing from us: Volto's own `View`
 * renders both around whatever it resolves out of
 * `config.views.contentTypesViews`, so a deployment can register into them
 * for a Profile or a group today. Nothing can be placed *inside* a view from
 * outside it, though, and directly under the heading is where what belongs to
 * the person rather than to the page reads as part of the name -- a badge, a
 * role, a team. So the views render that slot themselves, both through this.
 *
 * ## Why this is a component rather than two calls
 *
 * `SlotRenderer`'s props are `GetSlotArgs`, which requires `location` and a
 * whole `Content`. It supplies neither: it reads `useLocation()` itself, and
 * every caller in Volto is a `.jsx` file, so nothing upstream typechecks the
 * shape its own docstring documents -- `<SlotRenderer name="aboveContent"
 * content={content} />`. Our content types are honest subsets of `Content`
 * (see `types/content.ts`), and our views are TypeScript, so the call needs
 * an assertion. It is made once, here, with the reason next to it, rather
 * than pasted into each view.
 * @module components/Views/BelowTitleSlot
 */
import React from 'react';

import SlotRenderer from '@plone/volto/components/theme/SlotRenderer/SlotRenderer';
import type { SlotRendererProps } from '@plone/volto/components/theme/SlotRenderer/SlotRenderer';

import type { GroupContent, ProfileUserContent } from '../../types';

interface BelowTitleSlotProps {
  content: ProfileUserContent | GroupContent;
}

const BelowTitleSlot: React.FC<BelowTitleSlotProps> = ({ content }) => (
  // `location` is left out because `SlotRenderer` overwrites it with its own
  // `useLocation()` before either the predicates or the components see it,
  // and `content` is one of ours rather than a Dublin Core object. Both are
  // what the component is documented to be called with.
  <SlotRenderer
    {...({ name: 'belowTitle', content } as unknown as SlotRendererProps)}
  />
);

export default BelowTitleSlot;

/**
 * Volto's personal-tools menu, replaced by this add-on's.
 *
 * Shadows `@plone/volto/components/manage/Toolbar/PersonalTools`
 * (Volto 19.3.0).
 *
 * WHY IT IS SHADOWED. Volto has no extension point here. The only pluggable
 * is `toolbar-user-menu`, at the end of the menu *list*, so the avatar block
 * above it cannot be touched without replacing this component -- and the menu
 * entries themselves cannot be reordered or removed at all.
 *
 * No code lives here. The component is `components/Toolbar/PersonalTools`,
 * with its tests and its stories beside it, and this file is the one line
 * that puts it in Volto's place -- a shadowed path is a wiring decision, not
 * somewhere to keep an implementation nothing can import by name.
 *
 * @module customizations/volto/components/manage/Toolbar/PersonalTools
 */
import PersonalTools from '@plone-collective/volto-identity/components/Toolbar/PersonalTools';

export default PersonalTools;

/**
 * Volto's toolbar, replaced by this add-on's.
 *
 * Shadows `@plone/volto/components/manage/Toolbar/Toolbar` (Volto 19.3.0).
 *
 * WHY IT IS SHADOWED. Volto has no extension point for the toolbar's user
 * button. `toolbar-personal` is a DOM id on a button in this component, not a
 * pluggable, so the icon it draws cannot be replaced without replacing the
 * component around it -- and that icon is the generic `user.svg`, which says
 * that somebody is signed in rather than who.
 *
 * No code lives here. The component is `components/Toolbar/Toolbar`, and this
 * file is the one line that puts it in Volto's place -- a shadowed path is a
 * wiring decision, not somewhere to keep an implementation nothing can import
 * by name.
 *
 * @module customizations/volto/components/manage/Toolbar/Toolbar
 */
import Toolbar from '@plone-collective/volto-identity/components/Toolbar/Toolbar';

export default Toolbar;

/**
 * Volto's personal-tools menu, replaced by this add-on's.
 *
 * Shadows `@plone/volto/components/manage/Toolbar/PersonalTools/PersonalTools`
 * (Volto 19.7.0). Volto's older path, `Toolbar/PersonalTools`, re-exports
 * this one, so every import of the menu reaches it.
 *
 * Not the older path itself. A shadow becomes a webpack alias without a `$`,
 * which matches as a prefix: shadowing `Toolbar/PersonalTools` would also
 * capture `Toolbar/PersonalTools/ActionsMenuItems` and every other module in
 * that folder, and the build could no longer reach them.
 *
 * WHY IT IS SHADOWED. The entries are the backend's `personal_tools` actions
 * since Volto 19.7, but the rest of the panel has no extension point: the
 * avatar block in the header cannot be touched, and `toolbar-user-menu`
 * offers a second way to add entries that the site's actions know nothing
 * about.
 *
 * No code lives here. The component is `components/Toolbar/PersonalTools`,
 * with its tests and its stories beside it, and this file is the one line
 * that puts it in Volto's place -- a shadowed path is a wiring decision, not
 * somewhere to keep an implementation nothing can import by name.
 *
 * @module customizations/volto/components/manage/Toolbar/PersonalTools/PersonalTools
 */
import PersonalTools from '@plone-collective/volto-identity/components/Toolbar/PersonalTools';

export default PersonalTools;

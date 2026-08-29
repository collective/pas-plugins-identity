/**
 * Volto's users-control-panel row, replaced by this add-on's.
 *
 * Shadows `@plone/volto/components/manage/Controlpanels/Users/RenderUsers`
 * (Volto 19.3.0).
 *
 * WHY IT IS SHADOWED. The row's {guilabel}`Edit` action is built inline and
 * Volto has no extension point in it, so where that action leads cannot be
 * changed without replacing the component. It led to the wrong form on the
 * wrong store for every user whose fields live in a Profile, which is most of
 * them.
 *
 * No code lives here. The component is
 * `components/ControlPanel/RenderUsers`, with its tests and its stories
 * beside it, and this file is the one line that puts it in Volto's place --
 * a shadowed path is a wiring decision, not somewhere to keep an
 * implementation nothing can import by name.
 *
 * @module customizations/volto/components/manage/Controlpanels/Users/RenderUsers
 */
import RenderUsers from '@plone-collective/volto-identity/components/ControlPanel/RenderUsers';

export default RenderUsers;

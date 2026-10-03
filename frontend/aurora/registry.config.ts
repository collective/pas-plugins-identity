import { addons } from '@plone/aurora/registry.config';

addons.push('@plone-collective/aurora-identity');
// Dev-only: adapts Vite to the shared ../packages layout. Never published.
addons.push('aurora-identity-harness');

export { addons };

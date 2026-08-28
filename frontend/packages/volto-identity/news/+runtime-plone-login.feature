`RAZZLE_IDENTITY_SHOW_PLONE_LOGIN` is now read at run time, so it no longer decides what is in the image.

It used to be read in the add-on's settings as `process.env.RAZZLE_IDENTITY_SHOW_PLONE_LOGIN`, written out literally — which webpack's DefinePlugin substitutes into the browser bundle while `pnpm build` runs. That made the answer a property of the built image: a value supplied to a running container reached the Node process and never the browser, so two sites wanting two answers needed two images.

The Login component now asks at render time instead, through Volto's own `runtimeConfig`. That resolves `process.env` on the server, filtered to `RAZZLE_*` with computed keys DefinePlugin cannot rewrite, and `window.env` on the client, which the server serialized into the page while rendering it. Both sides therefore see the same value and the server-rendered markup matches what React hydrates — which reading `window.env` directly would not have given, since the server would render the default and the browser the real answer.

`config.settings.identityShowPloneLogin` remains as the default and is still `false`, so a project shipping its own default keeps it and the environment overrides it. The word `false` still reads as off rather than as a non-empty string. The frontend `Dockerfile` no longer takes it as a build argument. @ericof

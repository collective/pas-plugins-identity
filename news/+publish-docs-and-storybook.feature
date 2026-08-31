The documentation and Storybook are built and published together as one site.

Storybook was deployed by `frontend.yml` straight to the root of the `gh-pages` branch, and the documentation was built and uploaded as an artifact that nothing ever published. Adding a docs deployment to that arrangement would have had the two halves overwriting each other, one per run, depending on which finished last.

They are now assembled by a single job and deployed once: the documentation at the root, Storybook under `/storybook/`. Neither builder deploys on its own — `docs.yaml` and `tmp-frontend-storybook.yml` upload artifacts named after the ref, and `tmp-docs-publish.yml` downloads both, so one artifact and one deployment mean neither half can clobber the other.

Storybook is built from `main.yml` rather than `frontend.yml`, only on the branch that publishes and only after the frontend jobs it would otherwise duplicate have passed. A skipped builder is handled rather than fatal: a docs-only change still publishes, falling back to the artifact name the skipped builder would have computed for this same ref.

The `storybook-deploy` config output is now `deploy-docs`, since it gates the whole site. The two `tmp-` workflows are forks of their `plone/meta` counterparts, which deploy on their own and cannot be composed this way; the prefix marks them as living here only until upstream grows the same capability.

This needs the repository's Pages source set to "GitHub Actions". @ericof

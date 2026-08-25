Every string the add-on renders is translatable. The login page, the callback, the first-login wait, the identities list, the user-menu entries, both control panels and the secret reveal formatted their text as literal English; all of them now define their messages and format them through `react-intl`, and the extracted catalogues carry the full set.

Nothing a reader sees changed in English: each message keeps as its `defaultMessage` the exact text the component used to hard-code. @ericof

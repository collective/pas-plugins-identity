import * as allExports from './index';
import reducers from './index';
import { describe, expect, it } from 'vitest';

describe('the reducer map', () => {
  it('registers every reducer this module exports', () => {
    // The map is what `config.addonReducers` receives, and it is written by
    // hand -- so a reducer can be exported, imported, tested and dispatched
    // to while never being mounted in the store. It fails silently: the
    // request succeeds and the result lands nowhere, which reads as a bug in
    // whatever component was selecting the missing slice. `userProfile`
    // shipped that way and presented as three unrelated bugs in the user
    // menu.
    const exported = Object.entries(allExports)
      .filter(
        ([name, value]) => name !== 'default' && typeof value === 'function',
      )
      .map(([name]) => name);

    expect(Object.keys(reducers).sort()).toEqual(exported.sort());
  });
});

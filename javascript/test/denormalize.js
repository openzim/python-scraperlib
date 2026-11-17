import test from 'ava';

import {
  REPLAY_MARKER,
  escapeDotSegments,
  unescapeDotSegments,
  denormalize,
  extractOriginalURLFunction,
} from '../src/wombatSetup.js';

test('unescapeDotSegments', (t) => {
  t.is(unescapeDotSegments('a/_../b'), 'a/../b');
  t.is(unescapeDotSegments('a/_./b'), 'a/./b');
  t.is(unescapeDotSegments('_.'), '.');
  t.is(unescapeDotSegments('_..'), '..');
  t.is(unescapeDotSegments(''), '');
  // look-alikes are left untouched
  t.is(unescapeDotSegments('a/.foo/b'), 'a/.foo/b');
  t.is(unescapeDotSegments('a/foo../b'), 'a/foo../b');
});

test('escapeUnescapeDotSegmentsRoundtrip', (t) => {
  for (const path of ['a/../b', 'a/./b', '..', '.', '', 'a/.foo/b']) {
    t.is(unescapeDotSegments(escapeDotSegments(path)), path);
  }
});

test('denormalizeRoundtrip', (t) => {
  const cases = [
    ['example.com/', 'https://example.com/'],
    ['example.com/resource', 'https://example.com/resource'],
    ['example.com/a/_../b', 'https://example.com/a/../b'],
    ['example.com/foo%2Fbar', 'https://example.com/foo%2Fbar'],
    [
      'example.com/résumé%2Frésumé',
      'https://example.com/r%C3%A9sum%C3%A9%2Fr%C3%A9sum%C3%A9',
    ],
    ['example.com/foo/bar?a=1&b=2', 'https://example.com/foo/bar?a=1&b=2'],
  ];
  for (const [zimPath, expected] of cases) {
    t.is(denormalize(zimPath), expected);
  }
});

test('denormalizeLossy', (t) => {
  // fuzzy-matched values can only be reconstructed to a plausible,
  // representative value, not byte-identical to the real original
  t.is(
    denormalize('youtube.fuzzy.replayweb.page/videoplayback?id=1576'),
    'https://googlevideo.com/videoplayback?id=1576',
  );
  // a query value's original `+`/`%20` (both decode to space) can't be told
  // apart once normalized; `+` is always used when reconstructing
  t.is(
    denormalize('example.com/foo?q=a b c+d'),
    'https://example.com/foo?q=a+b+c%2Bd',
  );
});

test('extractOriginalURLFunctionMarked', (t) => {
  t.is(
    extractOriginalURLFunction(REPLAY_MARKER + 'example.com/foo/bar?a=1'),
    'https://example.com/foo/bar?a=1',
  );
});

test('extractOriginalURLFunctionUnmarkedFallsBackToUndefined', (t) => {
  t.is(extractOriginalURLFunction('_zim_static/wombat.js'), undefined);
});

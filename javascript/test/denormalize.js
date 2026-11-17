import test from 'ava';

import {
  REPLAY_MARKER,
  escapeDotSegments,
  unescapeDotSegments,
  denormalize,
  extractOriginalURLFunction,
  urlRewriteFunction,
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

test('extractOriginalURLFunction', (t) => {
  // `escapedPath` here is the value *after* wombat.js's extractOriginalURL
  // hook has already stripped its own wb_abs_prefix/wb_rel_prefix off --
  // which, since those are derived from `wb_info.prefix` (itself already
  // carrying REPLAY_MARKER), has already consumed the marker too: no
  // REPLAY_MARKER of its own survives in `escapedPath` (see
  // extractOriginalURLFunctionRealisticRoundtrip for the full, real path
  // through urlRewriteFunction's own percent-encoding).
  t.is(
    extractOriginalURLFunction('example.com/foo/bar?a=1'),
    'https://example.com/foo/bar?a=1',
  );
});

test('extractOriginalURLFunctionFallsBackToUndefinedOnBadInput', (t) => {
  // A lone '%' is not valid percent-encoding; decodeURIComponent throws,
  // and the hook must fall back to `undefined` (letting wombat.js's own
  // default heuristic take over) instead of propagating the exception.
  t.is(extractOriginalURLFunction('example.com/100%'), undefined);
});

test('extractOriginalURLFunctionRealisticRoundtrip', (t) => {
  // Exercises the real path: urlRewriteFunction's served, percent-encoded
  // output (only '/', '=' and ',' literal, see its own encodeURIComponent
  // chain), stripped of the serving prefix exactly like the wombat.js
  // extractOriginalURL hook does (`i.substr(e)`, which consumes
  // REPLAY_MARKER along with the rest of the prefix), must decode back
  // through extractOriginalURLFunction to the original URL -- in
  // particular, a character folded into the path and then percent-escaped
  // for serving (here the '?' in a query value containing a raw,
  // un-encoded URL, as docs.python.org-style pages do, see
  // openzim/warc2zim#471) must come back as a literal, not stay escaped.
  const prefix =
    'http://library.kiwix.org/content/myzim_yyyy-mm/' + REPLAY_MARKER;
  const originalUrl =
    'https://example.com/improve-page.html?pageurl=https:/other.example/foo';
  const rewritten = urlRewriteFunction(
    prefix + 'example.com/index.html',
    'example.com',
    'https',
    'https://example.com/index.html',
    prefix,
    originalUrl,
    undefined,
    undefined,
    undefined,
  );
  t.true(rewritten.startsWith(prefix));
  t.is(extractOriginalURLFunction(rewritten.slice(prefix.length)), originalUrl);
});

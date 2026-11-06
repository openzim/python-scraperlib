import test from 'ava';

import utils from '../src/wombatSetup.js';

test.beforeEach((t) => {
  t.context.prefix = 'http://library.kiwix.org/content/myzim_yyyy-mm/';
  t.context.originalHost = 'www.example.com';
  t.context.originalScheme = 'https';
});

test('escapeDotSegmentsDot', (t) => {
  t.is(utils.escapeDotSegments('a/./b'), 'a/_./b');
});

test('escapeDotSegmentsDotDot', (t) => {
  t.is(utils.escapeDotSegments('a/../b'), 'a/_../b');
});

test('escapeDotSegmentsTrailingDotDot', (t) => {
  t.is(utils.escapeDotSegments('a/..'), 'a/_..');
});

test('escapeDotSegmentsConsecutive', (t) => {
  t.is(utils.escapeDotSegments('a/../../b'), 'a/_../_../b');
});

test('escapeDotSegmentsLookAlikesUntouched', (t) => {
  t.is(
    utils.escapeDotSegments('a/.foo/foo../..foo/.../b'),
    'a/.foo/foo../..foo/.../b',
  );
});

test('randomUUIDFromBytesFormat', (t) => {
  const bytes = new Uint8Array([
    0x12, 0x34, 0x56, 0x78, 0x9a, 0xbc, 0xde, 0xf0, 0x11, 0x22, 0x33, 0x44,
    0x55, 0x66, 0x77, 0x88,
  ]);
  // byte 6's high nibble is forced to 4 (version) and byte 8's two top bits
  // to 10 (variant), per RFC 4122, regardless of the input
  t.is(
    utils.randomUUIDFromBytes(bytes),
    '12345678-9abc-4ef0-9122-334455667788',
  );
});

test('randomUUIDFromBytesIsRfc4122Compliant', (t) => {
  const bytes = new Uint8Array(16);
  for (let i = 0; i < 16; i++) bytes[i] = 0xff;
  t.regex(
    utils.randomUUIDFromBytes(bytes),
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
  );
});

test('nominalWbInfo', (t) => {
  const path = 'path1/resource1.js';
  const originalUrl =
    t.context.originalScheme + '://' + t.context.originalHost + '/' + path;
  const wmInfo = utils.getWombatInfo(
    t.context.prefix + path,
    t.context.originalHost,
    t.context.originalScheme,
    originalUrl,
    t.context.prefix,
  );
  t.is(wmInfo.coll, '');
  t.is(wmInfo.convert_post_to_get, true);
  t.is(wmInfo.enable_auto_fetch, false);
  t.is(wmInfo.isSW, false);
  t.is(wmInfo.is_framed, false);
  t.is(wmInfo.is_live, false);
  t.is(wmInfo.mod, '');
  t.is(wmInfo.prefix, t.context.prefix);
  t.is(wmInfo.proxy_magic, '');
  t.is(wmInfo.request_ts, '');
  t.is(wmInfo.static_prefix, t.context.prefix + '_zim_static/');
  t.is(wmInfo.target_frame, '___wb_replay_top_frame');
  t.is(wmInfo.timestamp, '');
  t.is(wmInfo.top_url, t.context.prefix + path);
  t.is(wmInfo.url, originalUrl);
  t.is(wmInfo.wombat_host, t.context.originalHost);
  t.deepEqual(wmInfo.wombat_opts, {});
  t.is(wmInfo.wombat_scheme, t.context.originalScheme);
  t.is(wmInfo.wombat_sec, 0);
  t.is(wmInfo.wombat_ts, '');
});

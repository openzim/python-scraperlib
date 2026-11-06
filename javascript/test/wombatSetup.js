import test from 'ava';
import nodeCrypto from 'node:crypto';

import utils from '../src/wombatSetup.js';

function textBytes(s) {
  return new TextEncoder().encode(s);
}

function nodeDigestHex(algorithm, bytes) {
  return nodeCrypto.createHash(algorithm).update(bytes).digest('hex');
}

function toHex(bytes) {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}

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

// Cross-validated against Node's own `crypto` module rather than hard-coded
// digests, covering the Merkle-Damgard padding's block-boundary edge cases (the
// input length lands exactly on, just under, and just over a 64-byte block once
// the mandatory `0x80` byte and 8-byte length suffix are accounted for).
const digestLengths = [
  0, 1, 3, 13, 55, 56, 57, 63, 64, 65, 119, 120, 121, 1000,
];

for (const length of digestLengths) {
  const bytes = new Uint8Array(length);
  for (let i = 0; i < length; i++) bytes[i] = (i * 37 + 11) % 256;

  test(`sha1BytesMatchesNodeCrypto-${length}`, (t) => {
    t.is(toHex(utils.sha1Bytes(bytes)), nodeDigestHex('sha1', bytes));
  });

  test(`sha256BytesMatchesNodeCrypto-${length}`, (t) => {
    t.is(toHex(utils.sha256Bytes(bytes)), nodeDigestHex('sha256', bytes));
  });
}

test('sha1BytesKnownVector', (t) => {
  // NIST/RFC well-known test vector
  t.is(
    toHex(utils.sha1Bytes(textBytes('abc'))),
    'a9993e364706816aba3e25717850c26c9cd0d89d',
  );
});

test('sha256BytesKnownVector', (t) => {
  // NIST/RFC well-known test vector
  t.is(
    toHex(utils.sha256Bytes(textBytes('abc'))),
    'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
  );
});

test('digestPolyfillStringAlgorithmName', async (t) => {
  const result = await utils.digestPolyfill('SHA-256', textBytes('abc'));
  t.true(result instanceof ArrayBuffer);
  t.is(
    toHex(new Uint8Array(result)),
    nodeDigestHex('sha256', textBytes('abc')),
  );
});

test('digestPolyfillObjectAlgorithmName', async (t) => {
  const result = await utils.digestPolyfill(
    { name: 'SHA-1' },
    textBytes('abc'),
  );
  t.is(toHex(new Uint8Array(result)), nodeDigestHex('sha1', textBytes('abc')));
});

test('digestPolyfillAcceptsTypedArrayView', async (t) => {
  const buf = new ArrayBuffer(20);
  const view = new Uint8Array(buf, 4, 3); // non-zero byteOffset, sub-length view
  view.set(textBytes('abc'));
  const result = await utils.digestPolyfill('SHA-256', view);
  t.is(
    toHex(new Uint8Array(result)),
    nodeDigestHex('sha256', textBytes('abc')),
  );
});

test('digestPolyfillAcceptsArrayBuffer', async (t) => {
  const result = await utils.digestPolyfill('SHA-256', textBytes('abc').buffer);
  t.is(
    toHex(new Uint8Array(result)),
    nodeDigestHex('sha256', textBytes('abc')),
  );
});

test('digestPolyfillRejectsUnsupportedAlgorithm', async (t) => {
  await t.throwsAsync(() => utils.digestPolyfill('SHA-384', textBytes('abc')));
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

import { fuzzyRules } from './fuzzyRules.js';
import URI from 'uri-js';

// Will be updated by rollup-plugin-version-injector
const VERSION = '[VI]version {version}, built on {date}[/VI]';
console.info(`Running wombat-setup ${VERSION}`);

// `crypto.randomUUID()` is restricted to secure contexts (HTTPS, or `localhost`), but
// ZIM content is commonly served over plain HTTP on a non-localhost host (LAN, offline
// hotspot, ...), where a page depending on it would otherwise throw instead of running.
// `crypto.getRandomValues()` has no such restriction, so polyfill `randomUUID` on top
// of it, producing a standard RFC 4122 v4 UUID, whenever it is missing.
export function randomUUIDFromBytes(bytes) {
  bytes[6] = (bytes[6] & 0x0f) | 0x40; // version 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant 10
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join(
    '',
  );
  return (
    hex.slice(0, 8) +
    '-' +
    hex.slice(8, 12) +
    '-' +
    hex.slice(12, 16) +
    '-' +
    hex.slice(16, 20) +
    '-' +
    hex.slice(20)
  );
}

if (
  typeof crypto !== 'undefined' &&
  typeof crypto.getRandomValues === 'function' &&
  typeof crypto.randomUUID !== 'function'
) {
  crypto.randomUUID = () =>
    randomUUIDFromBytes(crypto.getRandomValues(new Uint8Array(16)));
}

// `crypto.subtle` (SubtleCrypto) is, like `randomUUID`, restricted to secure
// contexts, and unlike `randomUUID` there is no lower-level primitive to build it
// from -- `digest()` needs an actual hash implementation. Polyfill the two
// algorithms observed in use (our own vendored wombat.js optionally uses SHA-1 for
// response ETags; archived pages have been seen using SHA-256 to derive a content
// id), matching the native `SubtleCrypto.digest(algorithm, data)` -> `Promise<ArrayBuffer>`
// contract, installed only when `crypto.subtle` itself is missing.

function rotl32(x, n) {
  return ((x << n) | (x >>> (32 - n))) >>> 0;
}

function rotr32(x, n) {
  return ((x >>> n) | (x << (32 - n))) >>> 0;
}

// Pads `bytes` to a whole number of 64-byte blocks, per the Merkle-Damgard
// construction shared by SHA-1 and SHA-256: a single `1` bit, as many `0` bits as
// needed, and the original bit length as a big-endian 64-bit integer.
function padForSha(bytes) {
  const bitLength = bytes.length * 8;
  const paddedLength = (bytes.length + 9 + 63) & ~63;
  const padded = new Uint8Array(paddedLength);
  padded.set(bytes);
  padded[bytes.length] = 0x80;
  const view = new DataView(padded.buffer);
  // `bitLength` safely fits a JS number up to 2^53 bits of input (far more than
  // this polyfill will ever realistically be asked to hash), so the high 32 bits
  // are obtained with a division rather than a (32-bit-truncating) bit shift.
  view.setUint32(paddedLength - 8, Math.floor(bitLength / 0x100000000), false);
  view.setUint32(paddedLength - 4, bitLength >>> 0, false);
  return padded;
}

export function sha1Bytes(bytes) {
  let [h0, h1, h2, h3, h4] = [
    0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476, 0xc3d2e1f0,
  ];
  const padded = padForSha(bytes);
  const view = new DataView(padded.buffer);
  const w = new Uint32Array(80);

  for (let offset = 0; offset < padded.length; offset += 64) {
    for (let i = 0; i < 16; i++) w[i] = view.getUint32(offset + i * 4, false);
    for (let i = 16; i < 80; i++) {
      w[i] = rotl32(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1);
    }

    let [a, b, c, d, e] = [h0, h1, h2, h3, h4];
    for (let i = 0; i < 80; i++) {
      let f, k;
      if (i < 20) {
        f = (b & c) | (~b & d);
        k = 0x5a827999;
      } else if (i < 40) {
        f = b ^ c ^ d;
        k = 0x6ed9eba1;
      } else if (i < 60) {
        f = (b & c) | (b & d) | (c & d);
        k = 0x8f1bbcdc;
      } else {
        f = b ^ c ^ d;
        k = 0xca62c1d6;
      }
      const temp = (rotl32(a, 5) + f + e + k + w[i]) >>> 0;
      e = d;
      d = c;
      c = rotl32(b, 30);
      b = a;
      a = temp;
    }
    h0 = (h0 + a) >>> 0;
    h1 = (h1 + b) >>> 0;
    h2 = (h2 + c) >>> 0;
    h3 = (h3 + d) >>> 0;
    h4 = (h4 + e) >>> 0;
  }

  const out = new Uint8Array(20);
  const outView = new DataView(out.buffer);
  [h0, h1, h2, h3, h4].forEach((h, i) => outView.setUint32(i * 4, h, false));
  return out;
}

const SHA256_K = [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
  0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
  0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
  0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
  0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
  0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

export function sha256Bytes(bytes) {
  let h = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c,
    0x1f83d9ab, 0x5be0cd19,
  ];
  const padded = padForSha(bytes);
  const view = new DataView(padded.buffer);
  const w = new Uint32Array(64);

  for (let offset = 0; offset < padded.length; offset += 64) {
    for (let i = 0; i < 16; i++) w[i] = view.getUint32(offset + i * 4, false);
    for (let i = 16; i < 64; i++) {
      const s0 =
        rotr32(w[i - 15], 7) ^ rotr32(w[i - 15], 18) ^ (w[i - 15] >>> 3);
      const s1 =
        rotr32(w[i - 2], 17) ^ rotr32(w[i - 2], 19) ^ (w[i - 2] >>> 10);
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
    }

    let [a, b, c, d, e, f, g, hh] = h;
    for (let i = 0; i < 64; i++) {
      const S1 = rotr32(e, 6) ^ rotr32(e, 11) ^ rotr32(e, 25);
      const ch = (e & f) ^ (~e & g);
      const temp1 = (hh + S1 + ch + SHA256_K[i] + w[i]) >>> 0;
      const S0 = rotr32(a, 2) ^ rotr32(a, 13) ^ rotr32(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const temp2 = (S0 + maj) >>> 0;
      hh = g;
      g = f;
      f = e;
      e = (d + temp1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (temp1 + temp2) >>> 0;
    }
    h = [
      (h[0] + a) >>> 0,
      (h[1] + b) >>> 0,
      (h[2] + c) >>> 0,
      (h[3] + d) >>> 0,
      (h[4] + e) >>> 0,
      (h[5] + f) >>> 0,
      (h[6] + g) >>> 0,
      (h[7] + hh) >>> 0,
    ];
  }

  const out = new Uint8Array(32);
  const outView = new DataView(out.buffer);
  h.forEach((hv, i) => outView.setUint32(i * 4, hv, false));
  return out;
}

export async function digestPolyfill(algorithm, data) {
  const name = (typeof algorithm === 'string' ? algorithm : algorithm.name)
    .toUpperCase()
    .replace('SHA', 'SHA-')
    .replace('SHA--', 'SHA-');
  const bytes =
    data instanceof ArrayBuffer
      ? new Uint8Array(data)
      : new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
  let out;
  if (name === 'SHA-1') out = sha1Bytes(bytes);
  else if (name === 'SHA-256') out = sha256Bytes(bytes);
  else
    throw new DOMException(
      'Unsupported digest algorithm: ' + algorithm,
      'NotSupportedError',
    );
  return out.buffer;
}

if (typeof crypto !== 'undefined' && typeof crypto.subtle === 'undefined') {
  crypto.subtle = { digest: digestPolyfill };
}

export function applyFuzzyRules(path) {
  // Apply fuzzy rules to simplify the ZIM path. First matching rule is applied and
  // result is immediately returned

  for (const rule of fuzzyRules) {
    const new_path = path.replace(new RegExp(rule.match), rule.replace);
    if (new_path != path) {
      return new_path;
    }
  }
  return path;
}

export function escapeDotSegments(path) {
  // Escape '.' and '..' path segments so they are not resolved as navigation.
  // Per RFC 3986, a '.' or '..' path segment is a dot-segment which any URI consumer
  // removes/resolves while normalizing a reference. A ZIM path must keep such a
  // segment as a literal entry name instead (e.g. one folded in from a querystring),
  // so it is prefixed with a '_', which is not itself special in a ZIM path.
  // Segments which only look like a dot-segment (e.g. 'foo..', '..foo', '...') are
  // not dot-segments and are left untouched.
  return path
    .split('/')
    .map((part) => (part === '.' || part === '..' ? '_' + part : part))
    .join('/');
}

export function hasAlreadyBeenRewritten(
  original_absolute_url,
  orig_url,
  uri,
  url,
) {
  // Detect (with a heuristic) that the path is most probably already rewritten and
  // must be kept as-is. We just need to detect relative links (all statically rewritten
  // links are relative) and contains a path including the hostname (which cannot be
  // joined with the orig_url since if it includes the hostname, it means it is in
  // another hostname than orig_url and will hence go one level too high in the path
  // hierarchy, hence working only on ZIM paths / relative links).
  // The heurisitic is:
  // - the link must be relative and start by going at least one level up
  // - the first non relative part of the path (i.e. not . or ..) looks like a hostname
  // (i.e. it contains a dot)
  // - the relative link, when merged with orig_url, is going exactly one "path level"
  // too high in the hierarchy
  if (typeof uri.scheme == 'undefined' && url.startsWith('../')) {
    const urlParts = url.split('/');
    const original_absolute_url1 = URI.resolve(
      orig_url,
      urlParts.slice(1).join('/'),
    );
    const original_absolute_url2 = URI.resolve(
      orig_url,
      urlParts.slice(2).join('/'),
    );
    // detect that relative link is going exactly one "path level" too high
    if (
      original_absolute_url1 == original_absolute_url &&
      original_absolute_url2 != original_absolute_url
    ) {
      const firstNonRelativePart = urlParts.find((urlPart) => urlPart !== '..');
      // detect that first non relative part of the path looks like a hostname
      if (firstNonRelativePart.indexOf('.') > -1) {
        // if all 3 conditions are true, then we assume it has already been rewritten
        return true;
      }
    }
  }
  // otherwise we don't know and assume it can be safely rewritten
  return false;
}

export function urlRewriteFunction(
  current_url, // The current (real) url we are on, e.g. http://library.kiwix.org/content/myzim_yyyy-mm/www.example.com/index.html
  orig_host, // The host of the original url, e.g. www.example.com
  orig_scheme, // The scheme of the original url, e.g. https
  orig_url, // The original url, e.g. https://www.example.com/index.html
  prefix, // The (absolute) prefix to add to all our urls (from where we are served), e.g. http://library.kiwix.org/content/myzim_yyyy-mm/
  url, // first argument passed by wombat.JS at each invocation, current url to rewrite, e.g. http://library.kiwix.org/content/myzim_yyyy-mm/www.example.com/image.png
  useRel,
  mod,
  doc, // last argument passed by wombat.JS at each invocation
) {
  if (!url) return url;

  // Transform URL which might be an object (detected on Chromium browsers at least)
  url = String(url);

  // Special stuff which is not really a URI but exists in the wild
  if (['#', '{', '*'].includes(url.substring(0, 1))) return url;

  // If URI scheme is defined but not http or https, we have to not rewrite the URL
  const uri = URI.parse(url);
  if (
    typeof uri.scheme !== 'undefined' &&
    !['http', 'https'].includes(uri.scheme)
  )
    return url;

  // If url starts with prefix, we need to remove this prefix before applying usual
  // rewrite rules
  if (url.startsWith(prefix)) {
    url = uri.scheme + '://' + url.substring(prefix.length);
  }

  // This is a hack to detect improper URL encoding ; proper detection should be
  // possible with chardet or other alternatives but did not worked so far ; we hence
  // take benefit of the error below to detect improper URL encoding
  // When improper URL encoding is detected, we try to encode URL as a best-effort;
  // 'best-effort', because if some part of the URL is encoded and another part is not,
  // this will fail ... but this is a weird edge case anyway
  try {
    decodeURIComponent(URI.parse(url).path);
  } catch (e) {
    url = encodeURI(url);
  }

  // Compute the absolute URI, just like the browser would have resolved it hopefully
  // We need to use the original URL for that to properly detect the hostname when
  // present ; current URL does not allow to do it easily
  const original_absolute_url = URI.resolve(orig_url, url);

  // Detect if url has probably already been rewritten and return as-is in such a case
  if (hasAlreadyBeenRewritten(original_absolute_url, orig_url, uri, url)) {
    return url;
  }

  // Detect (with a heuristic) that the path is most probably already rewritten and
  // must be kept as-is. We just need to detect relative links (all statically rewritten
  // links are relative) and contains a path including the hostname (which cannot be
  // joined with the orig_url since if it includes the hostname, it means it is in
  // another hostname than orig_url and will hence go one level too high in the path
  // hierarchy, hence working only on ZIM paths / relative links).
  // The heurisitic is:
  // - the link must be relative and start by going at least one level up
  // - the first non relative part of the path (i.e. not . or ..) looks like a hostname
  // (i.e. it contains a dot)
  // - the relative link, when merged with orig_url, is going exactly one "path level"
  // too high in the hierarchy
  if (typeof uri.scheme == 'undefined' && url.startsWith('../')) {
    const urlParts = url.split('/');
    const original_absolute_url1 = URI.resolve(
      orig_url,
      urlParts.slice(1).join('/'),
    );
    const original_absolute_url2 = URI.resolve(
      orig_url,
      urlParts.slice(2).join('/'),
    );
    // detect that relative link is going exactly one "path level" too high
    if (
      original_absolute_url1 == original_absolute_url &&
      original_absolute_url2 != original_absolute_url
    ) {
      const firstNonRelativePart = urlParts.find((urlPart) => urlPart !== '..');
      // detect that first non relative part of the path looks like a hostname
      if (firstNonRelativePart.indexOf('.') > -1) {
        // if all 3 conditions are true, then we do not rewrite the link at all,
        // otherwise we continue with normal rewritting
        return url;
      }
    }
  }

  // We now have to transform this absolute URI into a normalized ZIM path entry
  const absolute_url_parts = URI.parse(original_absolute_url);

  // Let's first compute the decoded host
  const serialized_host = URI.serialize(
    URI.parse('http://' + absolute_url_parts.host), // fake URI to benefit from decoding
    { iri: true }, // decode potentially puny-encoded host
  );
  const decoded_host = serialized_host.substring(7, serialized_host.length - 1);

  // And the decoded path, only exception is that an empty path must resolve to '/' path
  // (our convention, just like in Python)
  const decoded_path =
    !absolute_url_parts.path || absolute_url_parts.path.length === 0
      ? '/'
      : decodeURIComponent(absolute_url_parts.path);

  // And the decoded query, only exception is that + sign must resolve to ' ' to avoid
  // confusion (our convention, just like in Python). The `+` -> ' ' substitution must
  // happen on the still-encoded query string, before decoding percent-escapes,
  // otherwise a value containing a literal `+` correctly percent-encoded as `%2B`
  // would get wrongly turned into a space once decodeURIComponent turns it back into
  // a raw `+` (same order as the Python implementation).
  const decoded_query =
    !absolute_url_parts.query || absolute_url_parts.query.length === 0
      ? ''
      : '?' + decodeURIComponent(absolute_url_parts.query.replaceAll('+', ' '));

  // combine all decoded parts to get the ZIM path
  // (consecutive slashes are kept, just like in Python)
  const zimPath = decoded_host + decoded_path + decoded_query;

  // apply the fuzzy rules to the ZIM path
  const fuzzifiedPath = applyFuzzyRules(zimPath);

  // escape '.' and '..' path segments so they are not resolved as navigation by the
  // reader once this ZIM path is turned into a URI
  const escapedPath = escapeDotSegments(fuzzifiedPath);

  // Reencode everything but '/' (we decode it afterwards for simplicity)
  const finalUrl =
    prefix +
    encodeURIComponent(escapedPath)
      .replaceAll('%2F', '/')
      .replaceAll('%3D', '=')
      .replaceAll('%2C', ',');

  console.debug(
    'urlRewriten:\n\t- current_url: ' +
      current_url +
      '\n\t- orig_host: ' +
      orig_host +
      '\n\t- orig_scheme: ' +
      orig_scheme +
      '\n\t- orig_url: ' +
      orig_url +
      '\n\t- prefix: ' +
      prefix +
      '\n\t- url: ' +
      url +
      '\n\t- useRel: ' +
      useRel +
      '\n\t- mod: ' +
      mod +
      '\n\t- doc: ' +
      doc +
      '\n\t- finalUrl: ' +
      finalUrl.toString() +
      '\n\t',
  );

  return finalUrl;
}

export function getWombatInfo(
  current_url, // The current (real) url we are on
  orig_host, // The host of the original url
  orig_scheme, // The scheme of the original url
  orig_url, // The original url
  prefix, // The (absolute) prefix to add to all our urls (from where we are served))
) {
  return {
    // The rewrite function used to rewrite our urls.
    rewrite_function: (url, useRel, mod, doc) =>
      urlRewriteFunction(
        current_url,
        orig_host,
        orig_scheme,
        orig_url,
        prefix,
        url,
        useRel,
        mod,
        doc,
      ),

    // Seems to be used only to send message to. We don't care ?
    top_url: current_url,

    // Seems to be used to generate url for blobUrl returned by SW.
    // We don't care (?)
    url: orig_url,

    // Use to timestamp message send to top frame. Don't care
    timestamp: '',

    // Use to send message to top frame and in default rewrite url function. Don't care
    request_ts: '',

    // The url on which we are served.
    prefix: prefix,

    // The default mod to use.
    mod: '',

    // Use to detect if we are framed (and send message to top frame ?)
    is_framed: false,

    // ??
    is_live: false,

    // Never used ?
    coll: '',

    // Set wombat if is proxy mode (we are not)
    proxy_magic: '',

    // This is the prefix on which we have stored our static files (needed by wombat).
    // Must not conflict with other url served.
    // Will be used by wombat to not rewrite back the url
    static_prefix: prefix + '_zim_static/',

    wombat_ts: '',

    // A delay in sec to apply to all js time (`Date.now()`, ...)
    wombat_sec: 0,

    // The scheme of the original url
    wombat_scheme: orig_scheme,

    // The host of the original url
    wombat_host: orig_host,

    // We are not running inside a service worker, wombat needs to know about it since
    // some "magic" URLs like blobs are not available
    isSW: false,

    // Convert all post request to get request
    convert_post_to_get: true,

    // Not used, we are not replaying in a frame
    target_frame: '___wb_replay_top_frame',

    // Not used, we are not running in live mode
    enable_auto_fetch: false,

    // Extra options, not used
    wombat_opts: {},
  };
}

export default {
  applyFuzzyRules: applyFuzzyRules,
  escapeDotSegments: escapeDotSegments,
  urlRewriteFunction: urlRewriteFunction,
  getWombatInfo: getWombatInfo,
  randomUUIDFromBytes: randomUUIDFromBytes,
  sha1Bytes: sha1Bytes,
  sha256Bytes: sha256Bytes,
  digestPolyfill: digestPolyfill,
};

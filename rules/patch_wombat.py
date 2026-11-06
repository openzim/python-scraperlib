"""Patch the vendored wombat.js with local, interim fixes for issues that
have been reported upstream (webrecorder/wombat) but are not fixed there
yet:

- fetch() converting POST (and other non-GET) requests to GET, the same
  way its XMLHttpRequest override already does (webrecorder/wombat#242).
- Location getters (`location.href`/`.pathname`/`.search`/...) preferring
  `wb_info.url` over re-deriving a value via `extractOriginalURL`
  (webrecorder/wombat#245).

This script is invoked via `execute_after` on the wombat.js `get_file` action
in openzim.toml, right after wombat.js is downloaded, so it runs on every
build. Each patch below is applied and checked independently, and is
idempotent: a wombat.js that is already patched (e.g. because `get_file`
skipped re-downloading it) is left untouched.
"""

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)

wombat_js = (
    Path(__file__)
    .joinpath("../../src/zimscraperlib/rewriting/statics/wombat.js")
    .resolve()
)

if not wombat_js.exists():
    logging.warning("Skipping wombat.js patching, file is missing")
    raise SystemExit(0)

# --- fetch() override ---------------------------------------------------
#
# Without this, wombat.js's `window.fetch` override only rewrites the
# request URL: it leaves method and body untouched. Any page that calls
# `fetch()` with a POST (rather than XMLHttpRequest) therefore has that
# POST sent, as-is, to a server that only replays GET-converted content
# baked into the ZIM at scrape time, and 404s. This is exactly how
# YouTube's embedded player fetches its InnerTube player-config
# (`/youtubei/v1/player`): the request 404s, the player's JSON.parse() of
# the error page throws, and video playback breaks right after the user
# clicks Play.
#
# A fix for this has been proposed upstream (webrecorder/wombat), but it
# uses wombat's own full postToGetUrl() conversion, which flattens the
# request body into the query string. That does not match how our own
# scrape-time tooling (warc2zim) currently names a POST-converted ZIM
# entry: just `<original-url>&__wb_method=<METHOD>`, with the body dropped
# entirely (this can be verified directly on a built ZIM, e.g. for the
# `youtubei/v1/player`, `youtubei/v1/next` and WAA `GenerateIT` entries).
# So, until that upstream fix ships *and* our own scrape-time POST naming
# is made to match it, this patch intentionally uses the simpler,
# body-dropping convention instead, to stay consistent with how ZIMs are
# actually built today.
#
# Only the plain `fetch(url, {method, body})` call form is patched here:
# that is the one that reaches this code with a still-pristine, unrewritten
# URL. A `fetch(new Request(url, {method, body}))` call is instead handled
# by the Request-constructor patch below; by the time it reaches here, the
# Request object already carries its final, rewritten GET url.
FETCH_ORIGINAL = (
    "if(this.$wbwindow.fetch){var p=this.$wbwindow.fetch;"
    "this.$wbwindow.fetch=function(e,r){var i;"
    "if(e instanceof Request){var o=t.rewriteUrl(e.url);"
    "e.__WB_no_unrewrite=!0,i=o===e.url?e:new Request(o,e),"
    "delete e.__WB_no_unrewrite}"
    "else e=t.rewriteUrl(e.toString()),i=new Request(e,r);"
    "return p.call(t.proxyToObj(this),i)}}"
)

FETCH_PATCHED = (
    "if(this.$wbwindow.fetch){var p=this.$wbwindow.fetch;"
    "this.$wbwindow.fetch=function(e,r){var i;"
    "if(t.wb_info&&t.wb_info.convert_post_to_get&&!(e instanceof Request)){"
    'var curMethod=((r&&r.method)||"GET").toUpperCase();'
    'if("GET"!==curMethod&&"HEAD"!==curMethod){'
    'var curUrl=e.toString(),sep=curUrl.indexOf("?")>-1?"&":"?";'
    'e=curUrl+sep+"__wb_method="+curMethod,'
    'r=Object.assign({},r,{method:"GET",body:undefined})'
    "}}"
    "if(e instanceof Request){var o=t.rewriteUrl(e.url);"
    "e.__WB_no_unrewrite=!0,i=o===e.url?e:new Request(o,e),"
    "delete e.__WB_no_unrewrite}"
    "else e=t.rewriteUrl(e.toString()),i=new Request(e,r);"
    "return p.call(t.proxyToObj(this),i)}}"
)

# --- Request constructor override ---------------------------------------
#
# Handles `new Request(url, {method, body})` (and `fetch(new Request(...))`,
# which goes through this same constructor first). `r` here is the closed-
# over *native* Request class (captured before the override replaces
# `window.Request`), so building via `new r(...)` does not recurse back
# into this override.
REQUEST_ORIGINAL = (
    "this.$wbwindow.Request&&this.$wbwindow.Request.prototype){"
    "var l=this.$wbwindow.Request;this.$wbwindow.Request=(r=this.$wbwindow.Request,"
    'function e(i,o){t.domConstructorErrorChecker(this,"Request",arguments);'
    'var n=o||{},s=i;switch(typeof i){case"string":s=t.rewriteUrl(i);break;'
    'case"object":if(s=i,i.url){var a=t.rewriteUrl(i.url);'
    "a!==i.url&&(s=new r(a,i))}else i.href&&(s=t.rewriteUrl(i.toString(),!0))}"
    "let h=!1;if(n&&n.referrer){var w=t.rewriteUrl(n.referrer);"
    "w!==n.referrer&&(n instanceof e?(n.__WB_no_unrewrite=!0,h=!0):n.referrer=w)}"
    "var c=new r(s,n);return h&&delete n.__WB_no_unrewrite,c}),"
    "this.$wbwindow.Request.prototype=l.prototype,"
    'Object.defineProperty(this.$wbwindow.Request.prototype,"constructor",'
    "{value:this.$wbwindow.Request}),"
    'this.overridePropExtract(this.$wbwindow.Request.prototype,"url"),'
    'this.overridePropExtract(this.$wbwindow.Request.prototype,"referrer")}'
)

REQUEST_PATCHED = (
    "this.$wbwindow.Request&&this.$wbwindow.Request.prototype){"
    "var l=this.$wbwindow.Request;this.$wbwindow.Request=(r=this.$wbwindow.Request,"
    'function e(i,o){t.domConstructorErrorChecker(this,"Request",arguments);'
    "if(t.wb_info&&t.wb_info.convert_post_to_get){"
    'var cm=((o&&o.method)||(i&&typeof i==="object"&&i.method)||"GET").toUpperCase();'
    'if("GET"!==cm&&"HEAD"!==cm){'
    'var cu=typeof i==="string"?i:'
    "(i&&i.url!==undefined?i.url:(i&&i.href!==undefined?i.toString():null));"
    "if(null!==cu){"
    'var csep=cu.indexOf("?")>-1?"&":"?",cnew=cu+csep+"__wb_method="+cm;'
    'if(typeof i==="string"||i.url===undefined){'
    'i=cnew,o=Object.assign({},o,{method:"GET",body:undefined})'
    "}else{"
    'i=new r(cnew,{method:"GET",body:undefined,headers:i.headers,'
    "credentials:i.credentials,mode:i.mode,cache:i.cache,redirect:i.redirect,"
    "referrer:i.referrer,referrerPolicy:i.referrerPolicy,integrity:i.integrity,"
    "keepalive:i.keepalive,signal:i.signal})"
    "}}}}"
    'var n=o||{},s=i;switch(typeof i){case"string":s=t.rewriteUrl(i);break;'
    'case"object":if(s=i,i.url){var a=t.rewriteUrl(i.url);'
    "a!==i.url&&(s=new r(a,i))}else i.href&&(s=t.rewriteUrl(i.toString(),!0))}"
    "let h=!1;if(n&&n.referrer){var w=t.rewriteUrl(n.referrer);"
    "w!==n.referrer&&(n instanceof e?(n.__WB_no_unrewrite=!0,h=!0):n.referrer=w)}"
    "var c=new r(s,n);return h&&delete n.__WB_no_unrewrite,c}),"
    "this.$wbwindow.Request.prototype=l.prototype,"
    'Object.defineProperty(this.$wbwindow.Request.prototype,"constructor",'
    "{value:this.$wbwindow.Request}),"
    'this.overridePropExtract(this.$wbwindow.Request.prototype,"url"),'
    'this.overridePropExtract(this.$wbwindow.Request.prototype,"referrer")}'
)

# --- WombatLocation constructor: record the initial served href -------
#
# `t` is `orig_loc` (the real Location being wrapped) and `e` is the
# Wombat instance. The minifier folded the statements that precede the
# constructor's `for (var prop in orig_loc)` loop into that loop's
# iterable expression via the comma operator, so the insertion point
# (recording the served href this WombatLocation was created with) has to
# be added as one more term of that same comma expression.
LOC_CTOR_ORIGINAL = (
    "e.initLocOverride(this,this.orig_setter,this.orig_getter),"
    "e.setLoc(this,t.href),t)this.hasOwnProperty(r)"
)

LOC_CTOR_PATCHED = (
    "e.initLocOverride(this,this.orig_setter,this.orig_getter),"
    "e.setLoc(this,t.href),this._wb_initial_href=t.href,t)this.hasOwnProperty(r)"
)

# --- Location getters: prefer wb_info.url -------------------------------
#
# `location.href`/`.pathname`/`.search`/... (and the equivalent anchor/area
# element properties, which share this same function) always re-derive
# their value from the real served href via `extractOriginalURL`, which can
# only reverse rewrites wombat itself performed. Our own urlRewriteFunction
# (javascript/src/wombatSetup.js) has to flatten a URL's path+query into one
# ZIM path string, escaping '?'/'&' into literal '%3F'/'%26' so they survive
# as path characters -- extractOriginalURL cannot reverse that, even though
# the real, correctly-delimited original URL is already available as
# `wb_info.url`.
#
# `this.wombat` is only set on a WombatLocation (not on an anchor/area
# element), so this only kicks in for `location.*`, and only as long as the
# served href hasn't changed since `_wb_initial_href` was recorded above
# (i.e. no client-side navigation happened since): a `history.pushState()`/
# `location.href = ...`/etc. still falls back to extractOriginalURL exactly
# as before, since wb_info.url has nothing to say about those.
GETLOC_ORIGINAL = (
    "b.prototype.makeGetLocProp=function(t,e){var r=this;return function(){"
    "if(this._no_rewrite)return e.call(this,t);"
    '"maybeHref"===t&&(t="href");'
    'var i=e.call(this,"href");'
    'return"href"===t?r.extractOriginalURL(i):"ancestorOrigins"===t?[]:'
    '(this._orig_href!==i&&r.setLoc(this,i),this["_"+t])'
    "}}"
)

GETLOC_PATCHED = (
    "b.prototype.makeGetLocProp=function(t,e){var r=this;return function(){"
    "if(this._no_rewrite)return e.call(this,t);"
    '"maybeHref"===t&&(t="href");'
    'var i=e.call(this,"href"),'
    "k=this.wombat&&r.wb_info&&r.wb_info.url&&i===this._wb_initial_href;"
    "return k&&(i=r.wb_info.url),"
    '"href"===t?k?i:r.extractOriginalURL(i):"ancestorOrigins"===t?[]:'
    '(this._orig_href!==i&&r.setLoc(this,i),this["_"+t])'
    "}}"
)

content = wombat_js.read_text(encoding="utf-8")

patches = [
    ("fetch()/Request() POST-to-GET conversion", FETCH_ORIGINAL, FETCH_PATCHED),
    ("fetch()/Request() POST-to-GET conversion", REQUEST_ORIGINAL, REQUEST_PATCHED),
    ("Location getters preferring wb_info.url", LOC_CTOR_ORIGINAL, LOC_CTOR_PATCHED),
    ("Location getters preferring wb_info.url", GETLOC_ORIGINAL, GETLOC_PATCHED),
]

for name, original, patched in patches:
    if patched in content:
        logging.info("%s: already patched, skipping", name)
    elif original in content:
        content = content.replace(original, patched)
        logging.info("%s: patched successfully", name)
    else:
        raise SystemExit(
            f"{name}: wombat.js does not match the expected (patched or "
            "unpatched) code -- the vendored wombat.js version likely "
            "changed, this patch needs to be re-derived against the new "
            "source"
        )

wombat_js.write_text(content, encoding="utf-8")

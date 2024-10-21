# Technical architecture

Currently only HTML, CSS and JS rewriting is described in this document.

## Fuzzy rules

Fuzzy rules are stored in `rules/rules.yaml`. This configuration file is then used by `rules/generateRules.py` to generate Python and JS code.

Should you update these fuzzy rules, you hence have to:

- regenerate Python and JS files by running `python rules/generateRules.py`
- bundle again Javascript `wombatSetup.js` (see below).

## Wombat configuration

Wombat configuration contains some static configuration and the dynamic URL rewriting, including fuzzy rules.

It is bundled by rollup with `cd javascript && yarn build-prod` and the result is pushed to proper scraper location for inclusion at build time.

Tests are available and run with `cd javascript && yarn test`.

## Transformation of URL into ZIM path

Transforming a URL into a ZIM path has to respect the ZIM specification: path must not be url-encoded (i.e. it must be decoded) and it must be stored as UTF-8.

WARC record stores the items URL inside a header named "WARC-Target-URI". The value inside this header is encoded, or more exactly it is "exactly what the browser sent at the HTTP level" (see https://github.com/webrecorder/browsertrix-crawler/issues/492 for more details).

It has been decided (by convention) that we will drop the scheme, the port, the username and password from the URL. Headers are also not considered in this computation.

Computation of the ZIM path is hence mostly straightforward:

- decode the hostname which is puny-encoded
- decode the path and query parameter which might be url-encoded

## URL rewriting

In addition to the computation of the relative path from the current document URL to the URL to rewrite, URL rewriting also consists in computing the proper ZIM path (with same operation as above) and properly encoding it so that the resulting URL respects [RFC 3986](https://datatracker.ietf.org/doc/html/rfc3986). Some important stuff has to be noted in this encoding.

- since the original hostname is now part of the path, it will now be url-encoded
- since the `?` and following query parameters are also part of the path (we do not want readers to drop them like kiwix-serve would do), they are also url-encoded

Below is an example case of the rewrite operation on an image URL found in an HTML document.

- Document original URL: `https://kiwix.org/a/article/document.html`
- Document ZIM path: `kiwix.org/a/article/document.html`
- Image original URL: `//xn--exmple-cva.com/a/resource/image.png?foo=bar`
- Image rewritten URL: `../../../ex%C3%A9mple.com/a/resource/image.png%3Ffoo%3Dbar`
- Image ZIM Path: `exémple.com/a/resource/image.png?foo=bar`

## JS Rewriting

JS Rewriting is a bit special because rules to apply are different wether we are using "classic" Javascript or "module" Javascript.

Detection of Javascript modules starts at the HTML level where we have a `<script type="module"  src="...">` tag. This tells us that file at src location is a Javascript module. From there we now that its subresources are also Javascript module.

Currently this detection is done on-the-fly, based on the fact that WARC items are processed in the same order that they have been fetched by the browser, and we hence do not need a multi-pass approach. Meaning that HTML will be processed first, then parent JS, then its dependencies, ... **This is a strong assumption**.

# Functional Architecture

## Enrich libzim functions

zimscraperlib has primitives to enrich libzim functions with some operations which are known to be shared across scrapers. See `zim` module.

## Handle videos

zimscraperlib has primitives to manipulate videos with some operations which are known to be shared across scrapers. See `video` module.

## Handle pictures

zimscraperlib has primitives to manipulate pictures with some operations which are known to be shared across scrapers. See `image` module.

## Store and rewrite mostly unmodified HTML, CSS and JS from online website

zimscraperlib also contains primitives to rewrite HTML, CSS and JS fetched online, to proper operate within a ZIM without heavy modifications. While originaly developped for warc2zim, some of these primitives are now also used for mindtouch scraper and others might follow, so they are shared in zimscraperlib. See `rewriting` module.

### ZIM storage

While storing web resources in a ZIM is mostly straightforward (we just transfer the raw bytes, after some modification for URL rewriting if needed), the decision of the path where the resource will be stored is very important.

This is purely conventional, even if ZIM specification has to be respected for proper operation in readers.

This function is responsible to compute the ZIM path where a given web resource is going to be stored.

While the URL is the only driver of this computation for now, zimscraperlib might have to consider other contextual data in the future. E.g. the resource to serve might by dynamic, depending not only on URL query parameters but also header(s) value(s).

### Fuzzy rules

Unfortunately, it is not always possible / desirable to store the resource with a simple transformation.

A typical situation is that some query parameters are dynamically computed by some Javascript code to include user tracking identifier, current datetime information, ...

When running again the same javascript code inside the ZIM, the URL will hence be slightly different because context has changed, but the same content needs to be retrieved.

zimscraperlib hence relies on fuzzy rules to transform/simplify some URLs when computing the ZIM path.

### URL Rewriting

zimscraperlib transforms (rewrites) URLs found in documents (HTML, CSS, JS, ...) so that they are usable inside the ZIM.

#### General case

One simple example is that we might have following code in an HTML document to load an image with an absolute URL:

```
  <img src="https://en.wikipedia.org/wiki/File:Kiwix_logo_v3.svg"></img>
```

The URL `https://en.wikipedia.org/wiki/File:Kiwix_logo_v3.svg` has to be transformed to a URL that it is usable inside the ZIM.

For proper reader operation, openZIM prohibits using absolute URLs, so this has to be a relative URL. This relative URL is hence dependant on the location of the resource currently being rewriten.

The table below gives some examples of what the rewritten URL is going to be, depending on the URL of the rewritten document.

| HTML document URL                     | image URL rewritten for usage inside the ZIM         |
| ------------------------------------- | ---------------------------------------------------- |
| `https://en.wikipedia.org/wiki/Kiwix` | `./File:Kiwix_logo_v3.svg`                           |
| `https://en.wikipedia.org/wiki`       | `./wiki/File:Kiwix_logo_v3.svg`                      |
| `https://en.wikipedia.org/waka/Kiwix` | `../wiki/File:Kiwix_logo_v3.svg`                     |
| `https://fr.wikipedia.org/wiki/Kiwix` | `../../en.wikipedia.org/wiki/File:Kiwix_logo_v3.svg` |

As can be seen on the last line (but this is true for all URLs), this rewriting has to take into account the convention saying at which ZIM path a given web resource will be stored.

#### Dynamic case

The explanation above more or less assumed that the transformations can be done statically, i.e zimscraperlib can open every known document, find existing URLs and replace them with their counterpart inside the ZIM.

While this is possible for HTML and CSS documents typically, it is not possible when the URL is dynamically computed. This is typically the case for JS documents, where in the general case the URL is not statically stored inside the JS code but computed on-the-fly by aggregating various strings and values.

Rewriting these computations is not deemed feasible due to the huge variety of situation which might be encountered.

A specific function is hence needed to rewrite URL **live in client browser**, intercept any function triggering a web request, transform the URL according to conventions (where we expect the resource to be located in the general case) and fuzzy rules.

_Spoiler: this is where we will rely on wombat.js from webrecorder team, since this dynamic interception is quite complex and already done quite neatly by them_

#### Fuzzy rules

The same fuzzy rules that have been used to compute the ZIM path from a resource URL have to be applied again when rewriting URLs.

While this is expected to serve mostly for the dynamic case, we still applies them on both side (staticaly and dynamicaly) for coherency.

### Documents rewriten statically

For now zimscraperlib rewrites HTML, CSS and JS documents. For CSS and JS, this mainly consists in replacing URLs. For HTML, we also have more specific rewritting necessary (e.g. to handle base href or redirects with meta).

No domain specific (DS) rules are applied like it is done in wabac.JS because these rules are already applied in Browsertrix Crawler. For the same reason, JSON is not rewritten anymore (URL do not need to be rewritten in JSON because these URLs will be used by JS, intercepted by wombat and dynamically rewritten).

JSONP callbacks are supposed to be rewritten but this has not been heavily tested.

Other types of documents are supposed to be either not feasible / not worth it (e.g. URLs inside PDF documents), meaningless (e.g. images, fonts) or planned for later due to limited usage in the wild (e.g. XML).

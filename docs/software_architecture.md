# Software architecture

Currently only HTML, CSS and JS rewriting is described in this document.

## HTML rewriting

HTML rewriting is purely static (i.e. before resources are written to the ZIM). HTML code is parsed with the [HTML parser from Python standard library](https://docs.python.org/3/library/html.parser.html).

A small header script is inserted in HTML code to initialize wombat.js which will wrap all JS APIs to dynamically rewrite URLs comming from JS.

This header script is generated using [Jinja2](https://pypi.org/project/Jinja2/) template since it needs to populate some JS context variables needed by wombat.js operations (original scheme, original url, ...).

## CSS rewriting

CSS rewriting is purely static (i.e. before resources are written to the ZIM). CSS code is parsed with the [tinycss2 Python library](https://pypi.org/project/tinycss2/).

## JS rewriting

### Static

Static JS rewriting is simply a matter of pure textual manipulation with regular expressions. No parsing is done at all.

### Dynamic

Dynamic JS rewriting is done with [wombat JS library](https://github.com/webrecorder/wombat). The same fuzzy rules that are used for static rewritting are injected into wombat configuration. Code to rewrite URLs is an adapted version of the code used to compute ZIM paths.

For wombat setup, including the URL rewriting part, we need to pass wombat configuration info. This code is developed in the `javascript` folder. For URL parsing, it relies on the [uri-js library](https://www.npmjs.com/package/uri-js). This javascript code is bundled into a single `wombatSetup.js` file with [rollup bundler](https://rollupjs.org), the same bundler used by webrecorder team to bundle wombat.

## Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (as of version 1.5.0).

## [1.6.3] - 2022-07-29

### Added

- `download.stream_file()` supports passing `headers` (scrapers were already expecting it)

## [1.6.2] - 2022-07-29

### Changed

- Fixed `filesystem.get_content_mimetype()` crashing on non-guessable byte stream

## [1.6.1] - 2022-07-26

### Changed

- Wider range of accepted lxml dependency version as 4.9.1 fixes a security issue

## [1.6.0] - 2022-05-23

## Added

- `Archive.get_metadata_item()` to retrieve full item instead of just value

### Changed

- Using pylibzim v1.1.0 (using libzim 7.2.1)
  - Adding duplicate entries now raises RuntimeError
  - filesize is fixed for larger ZIMs

## [1.5.0] - 2022-05-09

### Added

- `zim.Archive.tags` and `zim.Archive.get_tags()` to retrieve parsed Tags
  with optionnal `libkiwix` param to include libkiwix's hints
- [tests] Counter tests now also uses a libzim6 file.

### Changed

- `zim.Archive.article_counter` follows libkiwix's new bahavior of
  returning libzim's `article_count` for libzim 7+ ZIMs and
  returning previously returned (parsed) value for older ZIMs.

### Removed

- Unreachable code removed in `imaging` module.
- [tests] “Sanskrit” removed from tests as output not predicatble depending on plaftform.


## [1.4.3]

* `zim.Archive.counters` wont fail on missing `Counter` metadata

## [1.4.2]

* Fixed leak in `zim.Archive`'s `.counters`
* New `.get_text_metadata()` method on `zim.Archive` to save UTF-8 decoding

## [1.4.1]

* New `Counter` metadata based properties for Archive:
  * `.counters`: parsed dict of the Counter metadata
  * `.article_counter`: libkiwix's calculation for nb or article
  * `.media_counter`: libkiwix's calculation for nb or media
* Fixed `i18n.find_language_names()` failing on some languages
* Added `uri` module with `rebuild_uri()`


## [1.4.0]

* Using new python-libzim based on libzim v7
  * New Creator API
  * Removed all namespace references
  * Renamed `url` mentions to `path`
  * Removed all links rewriting
  * Removed Article/CSS/Binary seggreation
  * Kept zimwriterfs mode (except it doesn't rewrite for namespaces)
  * New `html` module for HTML document manipulations
  * New callback system on `add_item_for()` and `add_item()`
  * New Archive API with easier search/suggestions and content access
* Changed download log level to DEBUG (was INFO)
* `filesystem.get_file_mimetype` now passes bytes to libmagic instead of filename due to release issue in libmagic
* safer `inputs.handle_user_provided_file` regarding input as str instead of Path
* `image.presets` and `video.presets` now all includes `ext` and `mimetype` properties
* Video convert log now DEBUG instead of INFO
* Fixed `image.save_image()` saving to disk even when using a bytes stream
* Fixed `image.transformation.resize_image()` when resizing a byte stream without a dst

## [1.3.6 (internal)]

Intermediate release using unreleased libzim to support development of libzim7.
Don't use it.

* requesting newer libzim version (not released ATM)
* New ZIM API for non-namespace libzim (v7)
* updated all requirements
* Fixed download test inconsistency
* fix_ogvjs mostly useless: only allows webm types
* exposing retry_adapter for refactoring
* Changed download log level to DEBUG (was INFO)
* guess more-defined mime from filename if magic says it's text
* get_file_mimetype now passes bytes to libmagic
* safer regarding input as str instead of Path
* fixed static item for empty content
* ext and mimetype properties for all presets
* Video convert log now DEBUG instead of INFO
* Added delete_fpath to add_item_for() and fixed StaticItem's auto remove
* Updated badges for new repo name

## [1.3.5]

* add `stream_file()` to stream content from a URL into a file or a `BytesIO` object
* deprecated `save_file()`
* fixed `add_binary` when used without an fpath (#69)
* deprecated `make_grayscale` option in image optimization
* Added support for in-memory optimization for PNG, JPEG, and WebP images
* allows enabling debug logs via ZIMSCRAPERLIB_DEBUG environ

## [1.3.4]

* added `wait` option in `YoutubeDownloader` to allow parallelism while using context manager
* do not use extension for finding format in `ensure_matches()` in `image.optimization` module
* added `VideoWebmHigh` and `VideoMp4High` presets for high quality WebM and Mp4 convertion respectively
* updated presets `WebpHigh`, `JpegMedium`, `JpegLow` and `PngMedium` in `image.presets`
* `save_image` moved from `image` to `image.utils`
* added `convert_image` `optimize_image` `resize_image` functions to `image` module

## [1.3.3]

* added `YoutubeDownloader` to `download` to download YT videos using a capped nb of threads

## [1.3.2]

* fixed rewriting of links with empty target
* added support for image optimization using `zimscraperlib.image.optimization` for webp, gif, jpeg and png formats
* added `format_for()` in `zimscraperlib.image.probing` to get PIL image format from the suffix

## [1.3.1]

* replaced BeautifoulSoup parser in rewriting (`html.parser` –> `lxml`)

## [1.3.0]

* detect mimetypes from filenames for all text files
* fixed non-filename based StaticArticle
* enable rewriting of links in poster attribute of audio element
* added find_language_in() and find_language_in_file() to get language from HTML content and HTML file respectively
* add a mime mapping to deal with inconsistencies in mimetypes detected by magic on different platforms
* convert_image signature changed:
  * `target_format` positional argument removed. Replaced with optionnal `fmt` key of keyword arguments.
  * `colorspace` optionnal positional argument removed. Replaced with optionnal `colorspace` key of keyword arguments.
* prevent rewriting of links with special schemes `mailto`, 'tel', etc. in HTML links rewriting
* replaced `imaging` module with exploded `image` module (`convertion`, `probing`, `transformation`)
* changed `create_favicon()` param names (`source_image` -> `src`, `dest_ico` -> `dst`)
* changed `save_image()` param names (`image` -> `src`)
* changed `get_colors()` param names (`image_path` -> `src`)
* changed `resize_image()` param names (`fpath` -> `src`)

## [1.2.1]

* fixed URL rewriting when running from /
* added support for link rewriting in `<object>` element
* prevent from raising error if element doesn't have the attribute with url
* use non greedy match for CSS URL links (shortest string matching `url()` format)
* fix namespace of target only if link doesn't have a netloc

## [1.2.0]

* added UTF8 to constants
* added mime_type discovery via magic (filesystem)
* Added types: mime types guessing from file names
* Revamped zim API
  * Removed ZimInfo which role was tu hold metadata for zimwriterfs call
  * Removed calling zimwriterfs binary but kept function name
  * Added zim.filesystem: zimwriterfs-like creation from a build folder
  * Added zim.creator: create files by manually adding each article
  * Added zim.rewriting: tools to rewrite links/urls in HTML/CSS
* add timeout and retries to save_file() and make it return headers

## [1.1.2]

* fixed `convert_image()` which tried to use a closed file

## [1.1.1]

* exposed reencode, Config and get_media_info in zimscraperlib.video
* added save_image() and convert_image() in zimscraperlib.imaging
* added support for upscaling in resize_image() via allow_upscaling
* resize_image() now supports params given by user and preservs image colorspace
* fixed tests for zimscraperlib.imaging

## [1.1.0]

* added video module with reencode, presets, config builder and video file probing
* `make_zim_file()` accepts extra kwargs for zimwriterfs

## [1.0.6]

* added translation support to i18n

## [1.0.5]

* added s3transfer to verbose dependencies list
* changed default log format to include module name

## [1.0.4]

* verbose dependencies (urllib3, boto3) now logged at WARNING level by default
* ability to set verbose dependencies log level and add modules to the list
* zimscraperlib's logging level now aligned with scraper's requested one


## [1.0.3]

* fix_ogvjs_dist script more generic (#1)
* updated zim to support other zimwriterfs params (#10)
* more flexible requirements for requests dependency

## [1.0.2]

* fixed return value of `get_language_details` on non-existent language
* fixed crash on `resize_image` with method `height`
* fixed root logger level (now DEBUG)
* removed useless `console=True` `getLogger` param
* completed tests (100% coverage)
* added `./test` script for quick local testing
* improved tox.ini
* added `create_favicon` to generate a squared favicon
* added `handle_user_provided_file` to handle user file/URL from param

## [1.0.1]

* fixed fix_ogvjs_dist

## [1.0.0]

* initial version providing
 * download: save_file, save_large_file
 * fix_ogvjs_dist
 * i18n: setlocale, get_language_details
 * imaging: get_colors, resize_image, is_hex_color
 * zim: ZimInfo, make_zim_file

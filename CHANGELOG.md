# 1.2.0

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

# 1.1.2

* fixed `convert_image()` which tried to use a closed file

# 1.1.1

* exposed reencode, Config and get_media_info in zimscraperlib.video
* added save_image() and convert_image() in zimscraperlib.imaging
* added support for upscaling in resize_image() via allow_upscaling
* resize_image() now supports params given by user and preservs image colorspace
* fixed tests for zimscraperlib.imaging

# 1.1.0

* added video module with reencode, presets, config builder and video file probing
* `make_zim_file()` accepts extra kwargs for zimwriterfs

# 1.0.6

* added translation support to i18n

# 1.0.5

* added s3transfer to verbose dependencies list
* changed default log format to include module name

# 1.0.4

* verbose dependencies (urllib3, boto3) now logged at WARNING level by default
* ability to set verbose dependencies log level and add modules to the list
* zimscraperlib's logging level now aligned with scraper's requested one


# 1.0.3

* fix_ogvjs_dist script more generic (#1)
* updated zim to support other zimwriterfs params (#10)
* more flexible requirements for requests dependency

# 1.0.2

* fixed return value of `get_language_details` on non-existent language
* fixed crash on `resize_image` with method `height`
* fixed root logger level (now DEBUG)
* removed useless `console=True` `getLogger` param
* completed tests (100% coverage)
* added `./test` script for quick local testing
* improved tox.ini
* added `create_favicon` to generate a squared favicon
* added `handle_user_provided_file` to handle user file/URL from param

# 1.0.1

* fixed fix_ogvjs_dist

# 1.0.0

* initial version providing
 * download: save_file, save_large_file
 * fix_ogvjs_dist
 * i18n: setlocale, get_language_details
 * imaging: get_colors, resize_image, is_hex_color
 * zim: ZimInfo, make_zim_file

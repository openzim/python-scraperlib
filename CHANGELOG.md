# dev

n/a

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

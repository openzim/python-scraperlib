import io
import pathlib

from zimscraperlib.constants import DEFAULT_ZIM_ILLLUSTRATION_SIZE
from zimscraperlib.image.conversion import convert_image, convert_svg2png
from zimscraperlib.image.optimization import optimize_png
from zimscraperlib.image.probing import format_for
from zimscraperlib.image.transformation import resize_image
from zimscraperlib.inputs import handle_user_provided_file


def get_zim_illustration(
    illustration_location: pathlib.Path | str,
    width: int = DEFAULT_ZIM_ILLLUSTRATION_SIZE,
    height: int = DEFAULT_ZIM_ILLLUSTRATION_SIZE,
    resize_method: str = "contain",
) -> io.BytesIO:
    """Get ZIM-ready illustration from any image path or URL

    illustration_location will be downloaded if needed. Image is automatically
    converted to PNG, resized and optimized as needed.

    Arguments:
        illustration_location: path or URL to an image
        width: target illustration width
        height: target illustration height
        resize_method: method to resize the image ; in general only 'contain' or
          'cover' make sense, but 'crop', 'width', 'height' and 'thumbnail' can be used
    """

    illustration_path = handle_user_provided_file(illustration_location)

    if not illustration_path:
        # given handle_user_provided_file logic, this is not supposed to happen besides
        # when empty string is passed, hence the simple error message
        raise ValueError("Illustration is missing")

    illustration = io.BytesIO()
    illustration_format = format_for(illustration_path, from_suffix=False)
    if illustration_format == "SVG":
        convert_svg2png(illustration_path, illustration, width, height)
    else:
        if illustration_format != "PNG":
            convert_image(illustration_path, illustration, fmt="PNG")
        else:
            illustration = io.BytesIO(illustration_path.read_bytes())
        resize_image(illustration, width, height, method=resize_method)

    optimized_illustration = io.BytesIO()
    optimize_png(illustration, optimized_illustration)

    return optimized_illustration

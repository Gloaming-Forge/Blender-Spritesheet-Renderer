"""Native Python spritesheet assembly using Pillow (PIL).

Replaces the former ImageMagick subprocess wrapper. All image operations are now
performed in-process using Pillow, eliminating the external ImageMagick dependency.
"""

import glob
import math
import os
from typing import Any, Dict, List, Tuple

from PIL import Image


def assemble_frames_into_spritesheet(
    sprite_size: Tuple[int, int],
    total_num_frames: int,
    temp_dir_path: str,
    output_file_path: str,
) -> Dict[str, Any]:
    """Assemble individual frame PNGs into a single spritesheet image.

    Returns a dict matching the legacy format:
        {
            "args": {
                "inputFiles": [...],
                "numColumns": int,
                "numRows": int,
                "outputFilePath": str,
                "outputImageSize": (width, height),
            },
            "stderr": str,
            "succeeded": bool,
        }
    """
    try:
        files = sorted(glob.glob(os.path.join(temp_dir_path, "*.png")))

        if total_num_frames <= 0:
            return {
                "args": _empty_args(files, output_file_path),
                "stderr": f"No frames to assemble (total_num_frames={total_num_frames})",
                "succeeded": False,
            }

        if len(files) != total_num_frames:
            return {
                "args": _empty_args(files, output_file_path),
                "stderr": f"Expected {total_num_frames} images, but found {len(files)} files",
                "succeeded": False,
            }

        num_rows = max(1, math.floor(math.sqrt(total_num_frames)))
        num_columns = math.ceil(total_num_frames / num_rows)

        sheet_w = num_columns * sprite_size[0]
        sheet_h = num_rows * sprite_size[1]

        sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))

        try:
            for i, frame_path in enumerate(files):
                with Image.open(frame_path) as frame:
                    x = (i % num_columns) * sprite_size[0]
                    y = (i // num_columns) * sprite_size[1]
                    sheet.paste(frame, (x, y))

            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
            sheet.save(output_file_path, "PNG")
        finally:
            sheet.close()

        args = {
            "inputFiles": files,
            "numColumns": num_columns,
            "numRows": num_rows,
            "outputFilePath": output_file_path,
            "outputImageSize": (sheet_w, sheet_h),
        }

        return {"args": args, "stderr": "", "succeeded": True}

    except Exception as e:
        return {
            "args": _empty_args([], output_file_path),
            "stderr": str(e),
            "succeeded": False,
        }


def pad_image_to_size(image_path: str, size: Tuple[int, int]) -> bool:
    """Pad an image with transparent pixels to reach the target size.

    The original image content stays anchored to the upper-left corner (NorthWest gravity).
    Raises on failure so the caller can report the error.
    """
    with Image.open(image_path) as img:
        if img.size == (size[0], size[1]):
            return True

        padded = Image.new("RGBA", (size[0], size[1]), (0, 0, 0, 0))
        padded.paste(img, (0, 0))

    padded.save(image_path, "PNG")
    padded.close()
    return True


def trim_and_resize_image_ignore_aspect(image_path: str, size: Tuple[int, int]) -> bool:
    """Trim transparent borders from an image, then resize to exact dimensions (ignoring aspect ratio).

    Raises on failure so the caller can report the error.
    """
    with Image.open(image_path) as img:
        rgba = img.convert("RGBA")

    # Trim: find the bounding box of non-transparent content
    bbox = rgba.getbbox()
    if bbox:
        cropped = rgba.crop(bbox)
        rgba.close()
        rgba = cropped

    # Resize to exact target, ignoring aspect ratio (matches ImageMagick's "!" flag).
    # NEAREST preserves sharp edges for pixel art / sprite content.
    resized = rgba.resize((size[0], size[1]), Image.Resampling.NEAREST)
    rgba.close()

    resized.save(image_path, "PNG")
    resized.close()
    return True


def _empty_args(files: List[str], output_file_path: str) -> Dict[str, Any]:
    """Return a minimal args dict for error cases."""
    return {
        "inputFiles": files,
        "numColumns": 0,
        "numRows": 0,
        "outputFilePath": output_file_path,
        "outputImageSize": (0, 0),
    }

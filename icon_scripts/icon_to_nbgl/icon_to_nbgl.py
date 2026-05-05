#!/usr/bin/env python3
"""
Convert a GIF/BMP/PNG icon to a hex-encoded NBGL device buffer.

Extracted from crypto-assets (icon_to_glyph.py + nbgl_rle.py),
originally from ledger-secure-sdk/lib_nbgl/tools.

Usage:
    pdm run icon-to-nbgl ICON_FILE [--size 14|48|64]
    or
    python scripts/icon_to_nbgl/icon_to_nbgl.py ICON_FILE [--size 14|48|64]

Prints the hex-encoded NBGL buffer to stdout.

Dependencies: Pillow
"""

import argparse
import gzip
import logging
import math
import re
import sys
from enum import IntEnum
from pathlib import Path

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# nbgl_rle.py (from ledger-secure-sdk/lib_nbgl/tools/nbgl_rle.py)
# ---------------------------------------------------------------------------

NB_MIN_PACKED_PIXELS = 3
NB_MAX_PACKED_PIXELS = 6

Repeat = int
Pixel = int
Occurrence = tuple[Repeat, Pixel]
Bpp = int


class ConversionException(Exception):
    pass


class Rle4bpp:
    @staticmethod
    def image_to_pixels(img: Image.Image, bpp: Bpp) -> list[Pixel]:
        width, height = img.size
        color_indexes = []
        nb_colors = pow(2, bpp)
        base_threshold = int(256 / nb_colors)
        half_threshold = int(base_threshold / 2)
        for col in reversed(range(width)):
            for row in range(height):
                color_index = img.getpixel((col, row))
                color_index = Pixel((color_index + half_threshold) / base_threshold)
                if color_index >= nb_colors:
                    color_index = nb_colors - 1
                color_indexes.append(color_index)
        return color_indexes

    @staticmethod
    def pixels_to_occurrences(pixels: list[Pixel]) -> list[Occurrence]:
        occurrences: list[Occurrence] = []
        for pixel in pixels:
            if len(occurrences) == 0:
                occurrences.append((pixel, 1))
            else:
                color, cnt = occurrences[-1]
                if pixel == color:
                    occurrences[-1] = (pixel, cnt + 1)
                else:
                    occurrences.append((pixel, 1))
        return occurrences

    @classmethod
    def fetch_next_single_pixels(cls, occurrences: list[Occurrence]) -> list[Pixel]:
        result = []
        for occurrence in occurrences:
            color, cnt = occurrence
            if cnt >= 2:
                break
            else:
                result.append(color)
        nb_pixels = len(result)
        if nb_pixels % NB_MAX_PACKED_PIXELS < NB_MIN_PACKED_PIXELS:
            return result[0 : (nb_pixels - nb_pixels % NB_MIN_PACKED_PIXELS)]
        return result

    @classmethod
    def generate_packed_single_pixels_bytes(cls, packed_occurrences: list[Pixel]) -> bytes:
        if len(packed_occurrences) < 3 or len(packed_occurrences) > 6:
            raise ConversionException(
                f"Invalid number of packed pixels {len(packed_occurrences)}, must be between 3 and 6"
            )
        header = (0b10 << 2) | (len(packed_occurrences) - 3)
        nibbles = [header]
        for occurrence in packed_occurrences:
            nibbles.append(occurrence)
        result = []
        for i, nibble in enumerate(nibbles):
            if (i % 2) == 0:
                result.append(nibble << 4)
            else:
                result[-1] += nibble
        return bytes(result)

    @classmethod
    def handle_packed_pixels(cls, packed_occurences: list[Pixel]) -> bytes:
        if len(packed_occurences) < 3:
            raise ConversionException(f"Invalid number of packed pixels {len(packed_occurences)}, must be at least 3")
        result = b""
        for i in range(0, len(packed_occurences), NB_MAX_PACKED_PIXELS):
            result += cls.generate_packed_single_pixels_bytes(packed_occurences[i : i + NB_MAX_PACKED_PIXELS])
        return result

    @staticmethod
    def handle_white_occurrence(occurrence: Occurrence) -> bytes:
        _, cnt = occurrence
        unit_cnt_max = 64
        result = []
        for i in range(0, cnt, unit_cnt_max):
            diff_cnt = cnt - i
            i_cnt = unit_cnt_max if diff_cnt > unit_cnt_max else diff_cnt
            result.append((0b11 << 6) | (i_cnt - 1))
        return bytes(result)

    @staticmethod
    def handle_non_white_occurrence(occurrence: Occurrence) -> bytes:
        color, cnt = occurrence
        unit_cnt_max = 8
        result = []
        for i in range(0, cnt, unit_cnt_max):
            diff_cnt = cnt - i
            i_cnt = unit_cnt_max if diff_cnt > unit_cnt_max else diff_cnt
            result.append((0 << 7) | (i_cnt - 1) << 4 | color)
        return bytes(result)

    @classmethod
    def occurrences_to_rle(cls, occurrences: list[Occurrence], bpp: Bpp) -> bytes:
        result = b""
        white_color = pow(2, bpp) - 1
        i = 0
        while i < len(occurrences):
            single_pixels = cls.fetch_next_single_pixels(occurrences[i:])
            if len(single_pixels) > 0:
                result += cls.handle_packed_pixels(single_pixels)
                i += len(single_pixels)
            else:
                occurrence = occurrences[i]
                color, _ = occurrence
                if color == white_color:
                    result += cls.handle_white_occurrence(occurrence)
                else:
                    result += cls.handle_non_white_occurrence(occurrence)
                i += 1
        return result

    @classmethod
    def rle_4bpp(cls, img: Image.Image) -> bytes:
        bpp = 4
        pixels = cls.image_to_pixels(img, bpp)
        occurrences = cls.pixels_to_occurrences(pixels)
        return cls.occurrences_to_rle(occurrences, bpp)


class Rle1bpp:
    @staticmethod
    def image_to_pixels(img: Image.Image, reverse: bool) -> list[Pixel]:
        width, height = img.size
        pixels = []
        white_threshold = 128
        if reverse:
            white_pixel = 0
            black_pixel = 1
        else:
            white_pixel = 1
            black_pixel = 0
        for col in reversed(range(width)):
            for row in range(height):
                if img.getpixel((col, row)) >= white_threshold:
                    pixels.append(white_pixel)
                else:
                    pixels.append(black_pixel)
        return pixels

    @staticmethod
    def encode_pass1(data: list[Pixel]) -> list[Occurrence]:
        output = []
        previous_value = -1
        count = 0
        for value in data:
            if value == previous_value:
                count += 1
            else:
                if count:
                    pair = (count, previous_value)
                    output.append(pair)
                previous_value = value
                count = 1
        if count:
            pair = (count, previous_value)
            output.append(pair)
        return output

    @staticmethod
    def encode_pass2(pairs: list[Occurrence]) -> bytes:
        max_count = 15
        next_pixel = 0
        alternances = []
        for repeat, value in pairs:
            if value != next_pixel:
                alternances.append(0)
                next_pixel ^= 1
            while repeat > max_count:
                alternances.append(max_count)
                repeat -= max_count
                alternances.append(0)
            if repeat:
                alternances.append(repeat)
                next_pixel ^= 1
        output = b""
        index = 0
        while index < len(alternances):
            zeros = alternances[index]
            index += 1
            if index < len(alternances):
                ones = alternances[index]
                index += 1
            else:
                ones = 0
            byte = (zeros << 4) | ones
            output += bytes([byte])
        return output

    @staticmethod
    def remove_duplicates(pairs: list[Occurrence]) -> list[Occurrence]:
        index = len(pairs) - 1
        while index >= 1:
            repeat1, value1 = pairs[index - 1]
            repeat2, value2 = pairs[index]
            if value1 == value2:
                repeat1 += repeat2
                pairs[index - 1] = (repeat1, value1)
                pairs.pop(index)
            index -= 1
        return pairs

    @classmethod
    def decode_pass2(cls, data: bytes) -> list[Occurrence]:
        pairs = []
        for byte in data:
            ones = byte & 0x0F
            byte >>= 4
            zeros = byte & 0x0F
            if zeros:
                pairs.append((zeros, 0))
            if ones:
                pairs.append((ones, 1))
        pairs = cls.remove_duplicates(pairs)
        return pairs

    @classmethod
    def rle_1bpp(cls, img: Image.Image, reverse: bool) -> bytes:
        pixels = cls.image_to_pixels(img, reverse)
        pairs = cls.encode_pass1(pixels)
        encoded_data = cls.encode_pass2(pairs)
        pairs2 = cls.decode_pass2(encoded_data)
        if pairs != pairs2:
            raise ConversionException("Error in RLE encoding/decoding pairs mismatch {pairs} != {pairs2}")
        return encoded_data


# ---------------------------------------------------------------------------
# icon_to_glyph.py (from ledger-secure-sdk/lib_nbgl/tools/icon2glyph.py)
# ---------------------------------------------------------------------------

NBGL_IMAGE_FILE_HEADER_SIZE = 8


class NbglFileCompression(IntEnum):
    NoCompression = 0
    Gzlib = 1
    Rle = 2


def check_glyph(file: Path, max_nb_colors: int, image_width_pixels: int, image_height_pixels: int) -> None:
    """
    Validate that a glyph is compliant for conversion to NBGL device format.
    """
    extension = file.suffix[1:].lower()
    if extension not in ["gif", "bmp", "png"]:
        raise ConversionException(f"Glyph extension should be '.gif', '.bmp', or '.png', not '.{extension}'")

    with Image.open(file) as img:
        if img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info:
            raise ConversionException("Glyph should have no alpha channel")

        colors = img.getcolors()
        if colors is None:
            raise ConversionException("Glyph should have the colors defined")
        num_colors = len(colors)

        if img.mode == "1":
            logger.debug("Monochrome image type")
            if num_colors != 2:
                raise ConversionException("Glyph should have only 2 colors")

            pixel_values = {v for _, v in colors}
            if 0 not in pixel_values:
                raise ConversionException("Glyph should have the black color defined")
            if pixel_values == {0}:
                raise ConversionException("Glyph should have the white color defined")

        elif img.mode in ("L", "P"):
            logger.debug("Grayscale image type")
            if num_colors > max_nb_colors:
                raise ConversionException(f"Glyph can't have more than {max_nb_colors} colors, {num_colors} found")

        else:
            raise ConversionException(f"Glyph should be Monochrome or Grayscale, it is {img.mode}")

        if img.width != image_width_pixels or img.height != image_height_pixels:
            raise ConversionException(f"Glyph should be {image_width_pixels}x{image_height_pixels}px")


def is_power2(n: int) -> bool:
    return n != 0 and ((n & (n - 1)) == 0)


def open_image(file_path: Path) -> tuple[Image.Image, Bpp] | None:
    if not file_path.exists():
        logger.error(f"File {file_path} does not exist")
        return None

    with Image.open(file_path) as i:
        im = i.convert("RGBA")
        new_image = Image.new("RGBA", im.size, "WHITE")
        new_image.paste(im, mask=im)
        im = new_image.convert("L")

        num_colors = len(im.getcolors())
        if num_colors > 16:
            num_colors = 16

        if not is_power2(num_colors):
            num_colors = int(pow(2, math.ceil(math.log(num_colors, 2))))

        bits_per_pixel = int(math.log(num_colors, 2))
        if bits_per_pixel > 1:
            bits_per_pixel = 4

        if bits_per_pixel == 0:
            bits_per_pixel = 1

        if bits_per_pixel == 1:
            im = ImageOps.invert(im)

        return im, bits_per_pixel


def image_to_packed_buffer(img: Image.Image, bpp: Bpp, reverse_1bpp: bool) -> bytes:
    width, height = img.size
    current_byte = 0
    current_bit = 0
    image_data = []
    nb_colors = pow(2, bpp)
    base_threshold = int(256 / nb_colors)
    half_threshold = int(base_threshold / 2)

    for col in reversed(range(width)):
        for row in range(height):
            color_index = img.getpixel((col, row))
            color_index = int((color_index + half_threshold) / base_threshold)
            if color_index >= nb_colors:
                color_index = nb_colors - 1
            if bpp == 1 and reverse_1bpp:
                color_index = (color_index + 1) & 0x1
            current_byte += color_index << ((8 - bpp) - current_bit)
            current_bit += bpp
            if current_bit >= 8:
                image_data.append(current_byte & 0xFF)
                current_bit = 0
                current_byte = 0

    if current_bit > 0:
        image_data.append(current_byte & 0xFF)

    return bytes(image_data)


def rle_compress(im: Image.Image, bpp: Bpp, reverse: bool) -> bytes:
    if bpp == 1:
        return Rle1bpp.rle_1bpp(im, reverse)
    elif bpp == 4:
        return Rle4bpp.rle_4bpp(im)
    else:
        raise ConversionException(f"Unsupported bpp {bpp} for RLE compression")


def gzlib_compress(im: Image.Image, bpp: Bpp, reverse: bool) -> bytes:
    pixels_buffer = image_to_packed_buffer(im, bpp, reverse)
    output_buffer = []
    full_uncompressed_size = len(pixels_buffer)
    i = 0
    while full_uncompressed_size > 0:
        chunk_size = min(2048, full_uncompressed_size)
        tmp = bytes(pixels_buffer[i : i + chunk_size])
        compressed_buffer = gzip.compress(tmp, mtime=0)
        output_buffer += [len(compressed_buffer) & 0xFF, (len(compressed_buffer) >> 8) & 0xFF]
        output_buffer += compressed_buffer
        full_uncompressed_size -= chunk_size
        i += chunk_size
    return bytearray(output_buffer)


def compress(im: Image.Image, bpp: Bpp) -> tuple[NbglFileCompression, bytes]:
    compressed_bufs = {
        NbglFileCompression.NoCompression: image_to_packed_buffer(im, bpp, False),
        NbglFileCompression.Gzlib: gzlib_compress(im, bpp, False),
        NbglFileCompression.Rle: rle_compress(im, bpp, False),
    }

    min_len = len(compressed_bufs[NbglFileCompression.NoCompression])
    min_comp = NbglFileCompression.NoCompression

    for compression, buffer in compressed_bufs.items():
        if buffer is None:
            continue
        final_length = len(buffer)
        if compression != NbglFileCompression.NoCompression:
            final_length += NBGL_IMAGE_FILE_HEADER_SIZE
        if min_len > final_length:
            min_len = final_length
            min_comp = compression

    return min_comp, compressed_bufs[min_comp]


def convert_to_image_file(
    image_data: bytes, width: int, height: int, bpp: Bpp, compression: NbglFileCompression
) -> bytes:
    bpp_formats = {1: 0, 2: 1, 4: 2}
    result = [
        width & 0xFF,
        width >> 8,
        height & 0xFF,
        height >> 8,
        (bpp_formats[bpp] << 4) | compression,
        len(image_data) & 0xFF,
        (len(image_data) >> 8) & 0xFF,
        (len(image_data) >> 16) & 0xFF,
    ]
    result.extend(image_data)
    return bytes(bytearray(result))


def compute_app_icon_data(
    image_path: Path, max_nb_colors: int, image_width_pixels: int, image_height_pixels: int
) -> bytes:
    """
    Process image as app icon and return NBGL byte buffer with headers.
    """
    check_glyph(image_path, max_nb_colors, image_width_pixels, image_height_pixels)

    opened = open_image(image_path)
    if opened is None:
        raise ConversionException(f"Failed to load image {image_path}")
    im, bpp = opened
    width, height = im.size
    compression, image_data = compress(im, bpp)
    image_data = convert_to_image_file(image_data, width, height, bpp, compression)
    return image_data


# ---------------------------------------------------------------------------
# Size -> validation params mapping
# ---------------------------------------------------------------------------

SIZE_SPECS: dict[int, tuple[int, int, int]] = {
    14: (2, 14, 14),
    48: (2, 48, 48),
    64: (16, 64, 64),
}

SIZE_PATTERN = re.compile(r"_(\d+)px\.")


def infer_size(filename: str) -> int | None:
    m = SIZE_PATTERN.search(filename)
    if m:
        size = int(m.group(1))
        if size in SIZE_SPECS:
            return size
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a GIF icon to a hex-encoded NBGL device buffer")
    parser.add_argument("icon_file", type=Path, help="Path to the icon file (.gif)")
    parser.add_argument(
        "--size",
        type=int,
        choices=[14, 48, 64],
        default=None,
        help="Icon size (inferred from filename if not provided)",
    )
    args = parser.parse_args()

    size = args.size
    if size is None:
        size = infer_size(args.icon_file.name)
    if size is None:
        print("Error: could not infer icon size from filename. Use --size.", file=sys.stderr)
        return 1

    max_nb_colors, w, h = SIZE_SPECS[size]

    try:
        data = compute_app_icon_data(args.icon_file, max_nb_colors, w, h)
    except ConversionException as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(data.hex())
    return 0


if __name__ == "__main__":
    sys.exit(main())

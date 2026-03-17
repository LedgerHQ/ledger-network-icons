#!/usr/bin/env bash
#
# Adapted from embedded-application-tools/icons/resize_icon.sh
# Generates 14px, 48px, and 64px chain icon GIFs from a source image.
#
# Prerequisites: ImageMagick (magick CLI)
#
# Usage: scripts/resize/resize_icon.sh [-k] INPUT_FILE CHAIN_ID
#   -k  Keep source image margins (skip crop-to-content)

set -e

resize_icon() {
    local OPTIND input_file target_size target_margin target_colors background_color output_file

    while getopts "i:s:m:c:b:o:" OPT
    do
        case "$OPT" in
            i) input_file="$OPTARG" ;;
            s) target_size="$OPTARG" ;;
            m) target_margin="$OPTARG" ;;
            c) target_colors="$OPTARG" ;;
            b) background_color="$OPTARG" ;;
            o) output_file="$OPTARG" ;;
            *) return ;;
        esac
    done
    mkdir -p "$(dirname "$output_file")"
    resize_target=$((target_size - (target_margin * 2)))
    args=()
    args+=(-background "$background_color")
    if [ "$target_colors" -eq 2 ]
    then
        args+=(-adaptive-resize "${resize_target}x${resize_target}")
    else
        args+=(-resize "${resize_target}x${resize_target}")
    fi
    args+=(-bordercolor "$background_color")
    args+=(-border "$target_margin")
    if [ "$target_colors" -eq 2 ]
    then
        args+=(-monochrome)
    else
        args+=(-type grayscale)
        args+=(-colors "$target_colors")
    fi
    magick "$input_file" "${args[@]}" "$output_file"
}

no_crop=false

while getopts "k" OPT
do
    case "$OPT" in
        k) no_crop=true ;;
        *)
            echo "Usage: $0 [-k] INPUT_FILE CHAIN_ID" >&2
            exit 1
            ;;
    esac
done
shift $((OPTIND-1))

if [ "$#" -ne 2 ]
then
    echo "Usage: $0 [-k] INPUT_FILE CHAIN_ID" >&2
    exit 1
fi

input_file="$1"
chain_id="$2"

ifile=/tmp/icon_resize_$$.gif

if ! "$no_crop"
then
    magick -background none "$input_file" -trim +repage "$ifile"
else
    cp "$input_file" "$ifile"
fi

width=$(identify -format "%w" "$ifile")
height=$(identify -format "%h" "$ifile")

if [ "$width" -ne "$height" ]
then
    mv "$ifile" "$ifile.old"
    if [ "$width" -gt "$height" ]
    then
        isize="$width"
    else
        isize="$height"
    fi
    magick "$ifile.old" \
        -background none \
        -gravity center \
        -extent "${isize}x${isize}" \
        "$ifile"
fi

bg_color="white"
out_dir="."

# 14px - Nano S Plus / Nano X (monochrome, no margin)
resize_icon -i "$ifile" \
            -s 14 \
            -m 0 \
            -c 2 \
            -b "$bg_color" \
            -o "${out_dir}/chain_${chain_id}_14px.gif"

# 48px - Apex (monochrome, 2px margin)
resize_icon -i "$ifile" \
            -s 48 \
            -m 2 \
            -c 2 \
            -b "$bg_color" \
            -o "${out_dir}/chain_${chain_id}_48px.gif"

# 64px - Stax / Flex (16-color grayscale, 3px margin)
resize_icon -i "$ifile" \
            -s 64 \
            -m 3 \
            -c 16 \
            -b "$bg_color" \
            -o "${out_dir}/chain_${chain_id}_64px.gif"

rm -f "$ifile" "$ifile.old"

echo "Generated:"
echo "  ${out_dir}/chain_${chain_id}_14px.gif"
echo "  ${out_dir}/chain_${chain_id}_48px.gif"
echo "  ${out_dir}/chain_${chain_id}_64px.gif"

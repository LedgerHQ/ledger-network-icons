# Ledger Network Icons

Icons for Ledger devices secure screens.
Only EVM networks are currently supported.

## Project Structure

```
├── icons/
│   └── ethereum/                  # EVM chain icons
│       ├── chain_1_14px.gif       # Nano S Plus / Nano X (monochrome)
│       ├── chain_1_48px.gif       # Apex (monochrome)
│       ├── chain_1_64px.gif       # Stax / Flex (16-color grayscale)
│       └── ...
├── icon_scripts/
│   ├── resize/
│   │   └── resize_icon.sh         # Generate icons from a source image
│   ├── validate/
│   │   └── validate_icons.py      # Validation script
│   └── icon_to_nbgl/
│       └── icon_to_nbgl.py        # Convert icon to NBGL device buffer
└── .github/workflows/
    └── ci.yml                     # CI/CD validation
```

## Icon Specs

| Size | Device | Colors | Margin |
|------|--------|--------|--------|
| 14px | Nano S Plus / Nano X | 2 (monochrome) | 0px |
| 48px | Apex | 2 (monochrome) | 2px |
| 64px | Stax / Flex | 16 (grayscale) | 3px |

## Prerequisites

- Python 3.12+
- [PDM](https://pdm-project.org/)
- ImageMagick CLI (only needed for icon resizing)

### ImageMagick dependency (optional)

ImageMagick CLI is only required to run `icon_scripts/resize/resize_icon.sh` for generating new icons.
It is **not** needed for validation (`validate-icons`) or conversion (`icon-to-nbgl`), which use Pillow.

On Ubuntu:
```
sudo apt-get install imagemagick
```
On MacOS:
```
brew install imagemagick
```

Information can be found here: https://docs.wand-py.org/

On MacOS, it may be necessary to set the `MAGICK_HOME` environment variable to the ImageMagick installation path
and to add the `bin` directory to the `PATH`, for example by adding the following lines to your shell configuration file:

```
export MAGICK_HOME=/opt/homebrew/opt/imagemagick/
export PATH="/opt/homebrew/opt/imagemagick/bin:$PATH"
```

## Setup

```bash
pdm install --dev
```

This installs all dependencies (including dev tools like pre-commit) and automatically sets up the git pre-commit hooks.

## Procedure to add a new network icon

1. Using a source icon of decent quality in GIF or PNG, run the resize script with the chain ID to use:

```bash
icon_scripts/resize/resize_icon.sh SOURCE_ICON.png 42161
```

This generates three files:
- `chain_42161_14px.gif`
- `chain_42161_48px.gif`
- `chain_42161_64px.gif`

If the quality is acceptable, copy them to `icons/ethereum/` folder.

2. Validate locally:

```bash
pdm run validate-icons
```

3. Commit, open a PR and ensure that the CI is green.

## To preview the NBGL Buffer used internally by the Ledger device

```bash
pdm run icon-to-nbgl icons/ethereum/chain_1_64px.gif
```

Prints the hex-encoded NBGL device buffer to stdout.

## CI/CD

GitHub Actions run automatically on every PR to:
- Validate all icons (dimensions, colors, format)
- Check naming convention and file pairing

## Next steps

Once the PR is submitted, the ledger team will take care of adding the network to the Ledger Crypto Asset List (CAL).

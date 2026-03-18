# Ledger Network Icons

Shared network chain icons for Ledger devices, used by [app-ethereum](https://github.com/LedgerHQ/app-ethereum) as a git submodule.

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
│   │   └── validate_icons.py      # CI validation
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
- Imagemagick

### Imagemagick dependency

- Imagemagick headers/libs are required for icon validation
- Imagemagick CLI is required to run `icon_scripts/resize/resize_icon.sh`

On Ubuntu, it can be installed with:
```
sudo apt-get install libmagickwand-dev
```
On MacOS, with:
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

## Add a New Network Icon

1. Run the resize script with your source icon and chain ID:

```bash
icon_scripts/resize/resize_icon.sh SOURCE_ICON.png 42161
```

This generates three files in `icons/ethereum/`:
- `chain_42161_14px.gif`
- `chain_42161_48px.gif`
- `chain_42161_64px.gif`

2. Validate locally:

```bash
pdm run validate-icons
```

3. Commit and open a PR. CI validates automatically.

## Convert Icon to NBGL Buffer

```bash
pdm run icon-to-nbgl icons/ethereum/chain_1_64px.gif
```

Prints the hex-encoded NBGL device buffer to stdout.

## CI/CD

GitHub Actions run automatically on every PR:
- Validates all icons (dimensions, colors, format)
- Checks naming convention and file pairing
EXFIX EXIF and file fix script
====================

### Overview

This Python script, `date_extractor.py`, is designed to extract and set dates for image files based on their EXIF data, filename, or path. It utilizes the `exiftool` command-line utility to update EXIF dates and the `os` module to modify filesystem timestamps.

### Features

* Automatic detection of the most precise date from EXIF data, filename, or path
* Manual specification of a date for setting
* Support for processing both individual files and directories recursively
* Compatibility with various image file formats

### Requirements

* Python 3.x
* `exiftool` command-line utility (install instructions provided in the script)

### Usage

The script can be run from the command line, providing either a single file path or a directory path as an argument. Optionally, a manual date can be specified for setting.

```bash
python3 date_extractor.py /path/to/image.jpg
python3 date_extractor.py /path/to/directory/
python3 date_extractor.py /path/to/image.jpg YYYY-MM-DD
```

### Manual Date Formats

When specifying a manual date, the following formats are supported:

* `%Y-%m-%d` (e.g., 2022-07-25)
* `%Y:%m:%d` (e.g., 2022:07:25)
* `%d-%m-%Y` (e.g., 25-07-2022)
* `%m-%d-%Y` (e.g., 07-25-2022)
* `%Y%m%d` (e.g., 20220725)
* `%Y-%m-%d %H:%M:%S` (e.g., 2022-07-25 14:30:00)
* `%Y:%m:%d %H:%M:%S` (e.g., 2022:07:25 14:30:00)

### Supported Image Formats

The script can process the following image file formats:

* `.jpg`
* `.jpeg`
* `.png`
* `.tiff`
* `.tif`
* `.bmp`
* `.gif`
* `.webp`
* `.heic`
* `.raw`
* `.cr2`
* `.nef`
* `.orf`
* `.arw`

### Example Use Cases

1. **Auto-detect date for a single file:**

```bash

python3 date_extractor.py /path/to/image.jpg

```

2. **Manual date specification for a single file:**

```bash
python3 date_extractor.py /path/to/image.jpg 2022-07-25
```

3. **Process a directory recursively with auto-detected dates:**

```bash
python3 date_extractor.py /path/to/directory/

```

4. **Process a directory with manual date specification:**

```bash
python3 date_extractor.py /path/to/directory/ 2022-07-25
```

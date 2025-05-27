#!/usr/bin/env python3

"""exfix.py - A tool to fix image dates using EXIF data, filename patterns, and file paths."""

import os
import re
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class DateExtractor:
    """Class to extract dates from EXIF data, filenames, and file paths."""

    def __init__(self):
        # Common date patterns in filenames and paths (ordered by specificity - most specific first)
        self.date_patterns = [
            # YYYY-MM-DD with time patterns (highest priority)
            (
                r"(\d{4})[_\-/](\d{1,2})[_\-/](\d{1,2})[_\-\s](\d{1,2})[:\-](\d{1,2})[:\-](\d{1,2})",
                "%Y-%m-%d-%H-%M-%S",
            ),
            (
                r"(\d{4})[_\-/](\d{1,2})[_\-/](\d{1,2})[_\-\s](\d{1,2})[:\-](\d{1,2})",
                "%Y-%m-%d-%H-%M",
            ),
            # Full date patterns
            (r"(\d{4})[_\-/](\d{1,2})[_\-/](\d{1,2})", "%Y-%m-%d"),
            (r"(\d{1,2})[_\-/](\d{1,2})[_\-/](\d{4})", "%d-%m-%Y"),
            (r"(\d{1,2})[_\-/](\d{1,2})[_\-/](\d{4})", "%m-%d-%Y"),
            (r"(\d{4})(\d{2})(\d{2})", "%Y%m%d"),
            # Date with 2-digit year
            (r"(\d{1,2})[_\-/](\d{1,2})[_\-/](\d{2})", "%d-%m-%y"),
            (r"(\d{2})[_\-/](\d{1,2})[_\-/](\d{1,2})", "%y-%m-%d"),
            # Month name patterns
            (r"(\d{1,2})([A-Za-z]{3})(\d{2,4})", "%d%b%y"),
            (r"([A-Za-z]{3})[_\-\s](\d{1,2})[_\-\s](\d{2,4})", "%b-%d-%y"),
            (r"(\d{2,4})[_\-\s]([A-Za-z]{3})[_\-\s](\d{1,2})", "%y-%b-%d"),
            # Year-Month patterns
            (r"(\d{4})[_\-/](\d{1,2})", "%Y-%m"),
            (r"(\d{4})(\d{2})", "%Y%m"),
            # Just year patterns (lowest priority but still valid)
            (r"(?:^|[^\d])(\d{4})(?:[^\d]|$)", "%Y"),
        ]

        # EXIF date fields to check (in order of preference)
        self.exif_date_fields = [
            "DateTimeOriginal",
            "CreateDate",
            "DateTime",
            "DateTimeDigitized",
            "ModifyDate",
            "FileModifyDate",
        ]

    def is_valid_date(self, dt):
        """Check if a date is reasonable/valid"""
        current_year = datetime.now().year

        # Filter out obviously invalid dates
        if dt.year < 1970 or dt.year > current_year + 1:
            return False

        # Check for common placeholder/invalid dates
        invalid_dates = [
            datetime(1010, 1, 1),  # Common camera placeholder
            datetime(1980, 1, 1),  # Another common placeholder
            datetime(1999, 1, 1),  # Y2K placeholder
            datetime(2000, 1, 1),  # Y2K placeholder
            datetime(1970, 1, 1),  # Unix epoch (often invalid)
        ]

        # Check if it's exactly one of the invalid dates (ignoring time)
        for invalid_date in invalid_dates:
            if (
                dt.year == invalid_date.year
                and dt.month == invalid_date.month
                and dt.day == invalid_date.day
            ):
                return False

        return True

    def extract_exif_dates(self, file_path):
        """Extract all available dates from EXIF data"""
        dates = []
        try:
            # Run exiftool to get JSON output
            result = subprocess.run(
                [
                    "exiftool",
                    "-json",
                    "-d",
                    "%Y:%m:%d %H:%M:%S",
                    "-DateTimeOriginal",
                    "-CreateDate",
                    "-DateTime",
                    "-DateTimeDigitized",
                    "-ModifyDate",
                    "-FileModifyDate",
                    str(file_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout:
                exif_data = json.loads(result.stdout)[0]

                for field in self.exif_date_fields:
                    if field in exif_data and exif_data[field]:
                        try:
                            dt = datetime.strptime(
                                exif_data[field], "%Y:%m:%d %H:%M:%S"
                            )
                            if self.is_valid_date(dt):
                                dates.append((dt, f"EXIF:{field}"))
                            else:
                                print(
                                    f"  Skipping invalid EXIF date: {dt.strftime('%Y-%m-%d %H:%M:%S')} from {field}"
                                )
                        except ValueError:
                            continue

        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            print(f"Warning: Could not read EXIF data from {file_path}")

        return dates

    def extract_filename_dates(self, file_path):
        """Extract dates from filename"""
        dates = []
        filename = Path(file_path).stem  # Get filename without extension

        for pattern, date_format in self.date_patterns:
            matches = re.finditer(pattern, filename, re.IGNORECASE)
            for match in matches:
                try:
                    if date_format == "%Y-%m-%d-%H-%M-%S":
                        # Full datetime
                        parts = match.groups()
                        dt = datetime(
                            int(parts[0]),
                            int(parts[1]),
                            int(parts[2]),
                            int(parts[3]),
                            int(parts[4]),
                            int(parts[5]),
                        )
                        if self.is_valid_date(dt):
                            dates.append((dt, f"filename:YYYY-MM-DD HH:MM:SS"))
                    elif date_format == "%Y-%m-%d-%H-%M":
                        # Date with hour and minute
                        parts = match.groups()
                        dt = datetime(
                            int(parts[0]),
                            int(parts[1]),
                            int(parts[2]),
                            int(parts[3]),
                            int(parts[4]),
                        )
                        if self.is_valid_date(dt):
                            dates.append((dt, f"filename:YYYY-MM-DD HH:MM"))
                    elif date_format == "%d%b%y":
                        # Special handling for month abbreviations (e.g., 25Jan23)
                        day, month, year = match.groups()
                        date_str = f"{day}{month}{year}"
                        dt = datetime.strptime(date_str, date_format)
                        if self.is_valid_date(dt):
                            dates.append((dt, f"filename:DD-MMM-YY"))
                    elif date_format in ["%b-%d-%y", "%y-%b-%d"]:
                        # Month name patterns
                        parts = match.groups()
                        if date_format == "%b-%d-%y":
                            month, day, year = parts
                        else:
                            year, month, day = parts
                        try:
                            dt = datetime.strptime(f"{month}-{day}-{year}", "%b-%d-%y")
                            if self.is_valid_date(dt):
                                dates.append((dt, f"filename:{date_format}"))
                        except ValueError:
                            continue
                    elif date_format == "%Y-%m":
                        # Year-Month - set to first day of month
                        year, month = match.groups()
                        dt = datetime(int(year), int(month), 1)
                        if self.is_valid_date(dt):
                            dates.append(
                                (dt, f"filename:YYYY-MM (set to 1st of month)")
                            )
                    elif date_format == "%Y%m":
                        # YYYYMM - set to first day of month
                        year_month = match.group(1)
                        year = int(year_month[:4])
                        month = int(year_month[4:])
                        dt = datetime(year, month, 1)
                        if self.is_valid_date(dt):
                            dates.append((dt, f"filename:YYYYMM (set to 1st of month)"))
                    elif date_format == "%Y":
                        # Just year - set to January 1st
                        year = match.group(1)
                        # Validate it's a reasonable year (1900-2100)
                        year_int = int(year)
                        if 1900 <= year_int <= 2100:
                            dt = datetime(year_int, 1, 1)
                            dates.append((dt, f"filename:YYYY (set to Jan 1st)"))
                    elif date_format in ["%d-%m-%Y", "%m-%d-%Y"]:
                        # Ambiguous formats - try both interpretations
                        parts = match.groups()
                        # Try DD-MM-YYYY first
                        try:
                            dt = datetime.strptime(
                                f"{parts[0]}-{parts[1]}-{parts[2]}", "%d-%m-%Y"
                            )
                            dates.append((dt, f"filename:DD-MM-YYYY"))
                        except ValueError:
                            pass
                        # Try MM-DD-YYYY
                        try:
                            dt = datetime.strptime(
                                f"{parts[0]}-{parts[1]}-{parts[2]}", "%m-%d-%Y"
                            )
                            dates.append((dt, f"filename:MM-DD-YYYY"))
                        except ValueError:
                            pass
                        continue
                    else:
                        # Standard date formats
                        if len(match.groups()) == 1:
                            date_str = match.group(1)
                        else:
                            date_str = "-".join(match.groups())
                        dt = datetime.strptime(
                            date_str, date_format.replace("_", "-").replace("/", "-")
                        )
                        dates.append((dt, f"filename:{date_format}"))

                except ValueError:
                    continue

        return dates

    def extract_path_dates(self, file_path):
        """Extract dates from file path"""
        dates = []
        path_parts = Path(file_path).parts

        for part in path_parts:
            for pattern, date_format in self.date_patterns:
                matches = re.finditer(pattern, part, re.IGNORECASE)
                for match in matches:
                    try:
                        if date_format == "%Y-%m-%d-%H-%M-%S":
                            # Full datetime
                            parts = match.groups()
                            dt = datetime(
                                int(parts[0]),
                                int(parts[1]),
                                int(parts[2]),
                                int(parts[3]),
                                int(parts[4]),
                                int(parts[5]),
                            )
                            if self.is_valid_date(dt):
                                dates.append((dt, f"path:YYYY-MM-DD HH:MM:SS"))
                        elif date_format == "%Y-%m-%d-%H-%M":
                            # Date with hour and minute
                            parts = match.groups()
                            dt = datetime(
                                int(parts[0]),
                                int(parts[1]),
                                int(parts[2]),
                                int(parts[3]),
                                int(parts[4]),
                            )
                            if self.is_valid_date(dt):
                                dates.append((dt, f"path:YYYY-MM-DD HH:MM"))
                        elif date_format == "%d%b%y":
                            # Month abbreviations
                            day, month, year = match.groups()
                            date_str = f"{day}{month}{year}"
                            dt = datetime.strptime(date_str, date_format)
                            if self.is_valid_date(dt):
                                dates.append((dt, f"path:DD-MMM-YY"))
                        elif date_format in ["%b-%d-%y", "%y-%b-%d"]:
                            # Month name patterns
                            parts = match.groups()
                            if date_format == "%b-%d-%y":
                                month, day, year = parts
                            else:
                                year, month, day = parts
                            try:
                                dt = datetime.strptime(
                                    f"{month}-{day}-{year}", "%b-%d-%y"
                                )
                                if self.is_valid_date(dt):
                                    dates.append((dt, f"path:{date_format}"))
                            except ValueError:
                                continue
                        elif date_format == "%Y-%m":
                            # Year-Month - set to first day of month
                            year, month = match.groups()
                            dt = datetime(int(year), int(month), 1)
                            if self.is_valid_date(dt):
                                dates.append(
                                    (dt, f"path:YYYY-MM (set to 1st of month)")
                                )
                        elif date_format == "%Y%m":
                            # YYYYMM - set to first day of month
                            year_month = match.group(1)
                            year = int(year_month[:4])
                            month = int(year_month[4:])
                            dt = datetime(year, month, 1)
                            if self.is_valid_date(dt):
                                dates.append((dt, f"path:YYYYMM (set to 1st of month)"))
                        elif date_format == "%Y":
                            # Just year - set to January 1st
                            year = match.group(1)
                            # Validate it's a reasonable year (1970-2100)
                            year_int = int(year)
                            if 1970 <= year_int <= 2100:
                                dt = datetime(year_int, 1, 1)
                                if self.is_valid_date(dt):
                                    dates.append((dt, f"path:YYYY (set to Jan 1st)"))
                        elif date_format in ["%d-%m-%Y", "%m-%d-%Y"]:
                            # Ambiguous formats - try both interpretations
                            parts = match.groups()
                            # Try DD-MM-YYYY first
                            try:
                                dt = datetime.strptime(
                                    f"{parts[0]}-{parts[1]}-{parts[2]}", "%d-%m-%Y"
                                )
                                if self.is_valid_date(dt):
                                    dates.append((dt, f"path:DD-MM-YYYY"))
                            except ValueError:
                                pass
                            # Try MM-DD-YYYY
                            try:
                                dt = datetime.strptime(
                                    f"{parts[0]}-{parts[1]}-{parts[2]}", "%m-%d-%Y"
                                )
                                if self.is_valid_date(dt):
                                    dates.append((dt, f"path:MM-DD-YYYY"))
                            except ValueError:
                                pass
                            continue
                        else:
                            # Standard date formats
                            if len(match.groups()) == 1:
                                date_str = match.group(1)
                            else:
                                date_str = "-".join(match.groups())
                            dt = datetime.strptime(
                                date_str,
                                date_format.replace("_", "-").replace("/", "-"),
                            )
                            if self.is_valid_date(dt):
                                dates.append((dt, f"path:{date_format}"))

                    except ValueError:
                        continue

        return dates

    def get_date_precision_score(self, source):
        """Calculate precision score for a date source (higher = more precise)"""
        # EXIF dates with full timestamp get highest priority
        if "EXIF:DateTimeOriginal" in source:
            return 100
        elif "EXIF:CreateDate" in source:
            return 95
        elif "EXIF:DateTime" in source:
            return 90
        elif "EXIF:DateTimeDigitized" in source:
            return 85
        elif "EXIF:ModifyDate" in source:
            return 80
        elif "EXIF:FileModifyDate" in source:
            return 75

        # Filename dates are next priority
        elif "filename:" in source:
            if "HH:MM:SS" in source:
                return 70  # Full datetime from filename
            elif "HH:MM" in source:
                return 65  # Date with time from filename
            elif any(
                fmt in source for fmt in ["DD-MM-YYYY", "MM-DD-YYYY", "YYYY-MM-DD"]
            ):
                return 60  # Full date from filename
            elif "YYYY-MM" in source:
                return 55  # Year-month from filename
            elif "YYYY" in source and "Jan 1st" in source:
                return 20  # Year only from filename
            else:
                return 50  # Other filename patterns

        # Path dates are lower priority
        elif "path:" in source:
            if "HH:MM:SS" in source:
                return 45  # Full datetime from path
            elif "HH:MM" in source:
                return 40  # Date with time from path
            elif any(
                fmt in source for fmt in ["DD-MM-YYYY", "MM-DD-YYYY", "YYYY-MM-DD"]
            ):
                return 35  # Full date from path
            elif "YYYY-MM" in source:
                return 30  # Year-month from path
            elif "YYYY" in source and "Jan 1st" in source:
                return 10  # Year only from path (lowest priority)
            else:
                return 25  # Other path patterns

        return 0  # Unknown source

    def get_best_date(self, file_path):
        """Find the most precise date from all sources"""
        all_dates = []

        # Get dates from all sources
        all_dates.extend(self.extract_exif_dates(file_path))
        all_dates.extend(self.extract_filename_dates(file_path))
        all_dates.extend(self.extract_path_dates(file_path))

        if not all_dates:
            return None, None

        # Remove duplicates while preserving source info
        unique_dates = []
        seen_dates = set()
        for date, source in all_dates:
            date_key = date.strftime("%Y-%m-%d %H:%M:%S")
            if date_key not in seen_dates:
                unique_dates.append((date, source))
                seen_dates.add(date_key)

        # Sort by precision score (descending) then by date (ascending for tie-breaking)
        unique_dates.sort(key=lambda x: (-self.get_date_precision_score(x[1]), x[0]))

        best_date, best_source = unique_dates[0]

        print(f"Found dates (sorted by precision):")
        for date, src in unique_dates:
            score = self.get_date_precision_score(src)
            marker = (
                " <- BEST (most precise)"
                if date == best_date and src == best_source
                else ""
            )
            print(
                f"  {date.strftime('%Y-%m-%d %H:%M:%S')} from {src} (score: {score}){marker}"
            )

        return best_date, best_source


def set_file_dates(file_path, target_date):
    """Set both EXIF and filesystem dates"""
    if not target_date:
        print("No valid date found to set")
        return False

    print(f"Setting date to: {target_date.strftime('%Y-%m-%d %H:%M:%S')}")

    # Format for exiftool
    exif_date_str = target_date.strftime("%Y:%m:%d %H:%M:%S")

    try:
        # Set EXIF dates
        subprocess.run(
            [
                "exiftool",
                "-overwrite_original_in_place",
                f"-DateTimeOriginal={exif_date_str}",
                f"-CreateDate={exif_date_str}",
                f"-DateTime={exif_date_str}",
                str(file_path),
            ],
            check=True,
            capture_output=True,
        )

        # Set filesystem dates
        timestamp = int(target_date.timestamp())
        os.utime(file_path, (timestamp, timestamp))

        print(f"Successfully updated dates for {file_path}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error running exiftool: {e}")
        return False
    except OSError as e:
        print(f"Error setting filesystem dates: {e}")
        return False


def process_file(file_path, manual_date=None):
    """Process a single file"""
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist")
        return False

    print(f"\nProcessing: {file_path}")

    if manual_date:
        # Use manually specified date
        try:
            # Try various date formats
            date_formats = [
                "%Y-%m-%d",
                "%Y:%m:%d",
                "%d-%m-%Y",
                "%m-%d-%Y",
                "%Y%m%d",
                "%Y-%m-%d %H:%M:%S",
                "%Y:%m:%d %H:%M:%S",
            ]
            target_date = None

            for fmt in date_formats:
                try:
                    target_date = datetime.strptime(manual_date, fmt)
                    break
                except ValueError:
                    continue

            if not target_date:
                print(f"Error: Could not parse date '{manual_date}'")
                return False

            print(
                f"Using manually specified date: {target_date.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        except Exception as e:
            print(f"Error parsing manual date: {e}")
            return False
    else:
        # Auto-detect best (most precise) date
        extractor = DateExtractor()
        target_date, source = extractor.get_best_date(file_path)

        if not target_date:
            print("No dates found in EXIF, filename, or path")
            return False

        print(f"Using most precise date from: {source}")

    return set_file_dates(file_path, target_date)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Auto-detect date:    python3 script.py /path/to/image.jpg")
        print("  Manual date:         python3 script.py /path/to/image.jpg YYYY-MM-DD")
        print(
            "  Manual date (time):  python3 script.py /path/to/image.jpg 'YYYY-MM-DD HH:MM:SS'"
        )
        print("  Process directory:   python3 script.py /path/to/directory/")
        print("  Directory + date:    python3 script.py /path/to/directory/ YYYY-MM-DD")
        sys.exit(1)

    path = sys.argv[1]
    manual_date = sys.argv[2] if len(sys.argv) > 2 else None

    # Check if exiftool is available
    try:
        subprocess.run(["exiftool", "-ver"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: exiftool not found. Please install exiftool first.")
        print("  Ubuntu/Debian: sudo apt install exiftool")
        print("  macOS: brew install exiftool")
        print("  Windows: Download from https://exiftool.org/")
        sys.exit(1)

    if os.path.isfile(path):
        # Process single file
        success = process_file(path, manual_date)
        sys.exit(0 if success else 1)

    elif os.path.isdir(path):
        # Process directory
        image_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".tiff",
            ".tif",
            ".bmp",
            ".gif",
            ".webp",
            ".heic",
            ".raw",
            ".cr2",
            ".nef",
            ".orf",
            ".arw",
        }

        processed = 0
        successful = 0

        for root, dirs, files in os.walk(path):
            for file in files:
                if Path(file).suffix.lower() in image_extensions:
                    file_path = os.path.join(root, file)
                    processed += 1
                    if process_file(file_path, manual_date):
                        successful += 1

        print(f"\nProcessed {processed} files, {successful} successful")

    else:
        print(f"Error: {path} is not a valid file or directory")
        sys.exit(1)


if __name__ == "__main__":
    main()

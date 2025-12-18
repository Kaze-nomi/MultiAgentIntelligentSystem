#!/usr/bin/env python3
"""
Script to create a file with specific content.

This script creates a file named 'arbuz_lover.txt' in the current directory
and writes the string 'Iamarbuzlover' to it.
"""

import os
import sys
from pathlib import Path


def validate_filename(filename: str, allowed_dir: str = '.') -> str:
    """
    Validate filename to prevent path traversal attacks.

    Args:
        filename: Name of the file to validate
        allowed_dir: Directory where file creation is allowed (default: current directory)

    Returns:
        Absolute path to the file within allowed directory

    Raises:
        ValueError: If path traversal is detected or filename is invalid
    """
    # Get absolute path of allowed directory
    allowed_abs = os.path.realpath(allowed_dir)

    # Additional check for path separators in filename
    if os.sep in filename or (os.altsep and os.altsep in filename):
        raise ValueError(f"Path separators not allowed in filename: {filename}")

    # Construct full path and normalize
    file_path = os.path.realpath(os.path.join(allowed_abs, filename))

    # Check if the resolved path is within allowed directory using commonpath
    # This prevents symlink attacks and works correctly on all platforms
    try:
        common = os.path.commonpath([allowed_abs, file_path])
        if os.path.realpath(common) != allowed_abs:
            raise ValueError(f"Path traversal detected: {filename}")
    except ValueError:
        # ValueError is raised by commonpath if paths are on different drives
        raise ValueError(f"Path traversal detected: {filename}")

    # Additional check to ensure we're not trying to write to the parent directory
    if os.path.dirname(file_path) != allowed_abs:
        raise ValueError(f"Path traversal detected: {filename}")

    return file_path


def create_file_with_content(filename: str, content: str) -> None:
    """
    Create a file with the specified content.

    Args:
        filename: Name of the file to create
        content: Content to write to the file

    Raises:
        OSError: If there's an error creating or writing to the file
        ValueError: If filename contains invalid path sequences
    """
    try:
        # Validate and get safe file path
        file_path = Path(validate_filename(filename))

        # Write content to file
        with file_path.open('w', encoding='utf-8') as f:
            f.write(content)

        print(f"Successfully created file: {file_path}")
        print(f"Content written: '{content}'")

    except OSError as e:
        print(f"Error creating file {filename}: {e}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        raise


def verify_file_content(filename: str, expected_content: str) -> bool:
    """
    Verify file exists and has the expected content.

    Args:
        filename: Name of the file to verify
        expected_content: Content expected to be in the file

    Returns:
        True if verification successful, False otherwise
    """
    try:
        file_path = Path(validate_filename(filename))
        with file_path.open('r', encoding='utf-8') as f:
            actual_content = f.read()
            return actual_content == expected_content
    except (OSError, ValueError):
        return False


def main():
    """Main function to execute the file creation."""
    # Define filename and content
    filename = "arbuz_lover.txt"
    content = "Iamarbuzlover"

    try:
        # Create the file
        create_file_with_content(filename, content)

        # Verify file exists and has correct content (atomic operation)
        if verify_file_content(filename, content):
            print("Verification successful: File content matches")
        else:
            print("Error: File verification failed")
            sys.exit(1)

    except Exception as e:
        print(f"Script failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

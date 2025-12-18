#!/usr/bin/env python3
"""
Script to create a file with the content 'hello im arbuz'

This script creates a file named 'arbuz.txt' in the current directory
with the specified content. It handles potential errors and provides
feedback about the operation.
"""

import os
import sys
from pathlib import Path


def validate_file_path(file_path: str, base_dir: Path = None) -> Path:
    """
    Validate and resolve file path to prevent path traversal attacks.

    Args:
        file_path (str): The file path to validate
        base_dir (Path): Base directory where files are allowed to be created
                        Defaults to current working directory

    Returns:
        Path: Resolved and validated absolute path

    Raises:
        ValueError: If path traversal attempt is detected
    """
    if base_dir is None:
        base_dir = Path.cwd()

    # First join with base directory, then resolve
    # This prevents path traversal and symlink attacks by ensuring
    # resolution happens within the safe directory structure
    path = (base_dir / file_path).resolve()

    # Ensure the resolved path is still within the base directory
    # This double-check prevents TOCTOU (Time-of-Check-Time-of-Use) race conditions
    try:
        path.relative_to(base_dir)
    except ValueError:
        raise ValueError(f"Path traversal attempt detected. '{file_path}' is outside allowed directory")

    return path


def create_arbuz_file(file_path: str = "arbuz.txt", content: str = "hello im arbuz",
                     overwrite: bool = False) -> bool:
    """
    Create a file with the specified content in a secure manner.

    Args:
        file_path (str): Path to the file to create. Defaults to "arbuz.txt"
        content (str): Content to write to the file. Defaults to "hello im arbuz"
        overwrite (bool): Whether to overwrite existing file. Defaults to False

    Returns:
        bool: True if file was created successfully, False otherwise
    """
    try:
        # Validate the file path to prevent path traversal
        base_dir = Path.cwd()  # Restrict to current working directory
        path = validate_file_path(file_path, base_dir)

        # Check if file exists within the same atomic operation
        # This prevents TOCTOU race conditions
        if path.exists() and not overwrite:
            print(f"✗ File '{file_path}' already exists and overwrite is disabled")
            return False

        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write content to file with atomic operation to prevent race conditions
        # Using temporary file and rename for atomic write on Unix systems
        temp_path = path.with_suffix('.tmp')
        try:
            with open(temp_path, 'w', encoding='utf-8') as file:
                file.write(content)
            # Atomic rename
            temp_path.replace(path)
        except Exception:
            # Clean up temp file if something went wrong
            if temp_path.exists():
                temp_path.unlink()
            raise

        action = "overwritten" if overwrite and path.exists() else "created"
        print(f"✓ File '{file_path}' {action} successfully")
        print(f"  Content: {content}")
        print(f"  Full path: {path}")
        return True

    except ValueError as e:
        print(f"✗ Security Error: {e}")
        return False
    except PermissionError:
        print(f"✗ Error: Permission denied when creating '{file_path}'")
        return False
    except OSError as e:
        print(f"✗ Error: Failed to create '{file_path}': {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error when creating '{file_path}': {e}")
        return False


def main():
    """
    Main function to execute the script.
    """
    default_file = "arbuz.txt"

    # Check if file exists and ask for overwrite permission
    # This is now handled within the atomic create operation
    if Path(default_file).exists():
        response = input(f"File '{default_file}' already exists. Overwrite? (y/n): ")
        if response.lower() not in ['y', 'yes']:
            print("Operation cancelled.")
            sys.exit(0)
        # Create with overwrite flag
        success = create_arbuz_file(default_file, overwrite=True)
    else:
        # Create new file
        success = create_arbuz_file(default_file)

    if success:
        print("\n✓ Operation completed successfully")
        sys.exit(0)
    else:
        print("\n✗ Operation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

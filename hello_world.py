#!/usr/bin/env python3
"""
Simple Hello World program.

This script prints 'Hello, World!' to the console.
"""

def main():
    """
    Main function that prints the greeting.
    """
    try:
        print("Hello, World!")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

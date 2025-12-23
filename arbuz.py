#!/usr/bin/env python3
"""
Simple script to print 'arbuz'.

This script demonstrates basic output functionality.
"""

def main():
    """
    Main function that prints 'arbuz'.
    """
    try:
        print("arbuz")
    except Exception as e:
        print(f"An error occurred: {e}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())

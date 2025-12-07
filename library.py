'''Library management module.'''

from typing import Dict, List, Optional, Tuple
from book import Book


class Library:
    """Manages a collection of books using ISBN as unique key.

    Attributes:
        books: Dictionary mapping ISBN to Book instances.
    """

    def __init__(self) -> None:
        """Initializes an empty library."""
        self.books: Dict[str, Book] = {}

    def add_book(self, book: Book) -> Tuple[bool, str]:
        """
        Adds a book to the library if it doesn't already exist.

        Args:
            book: The Book instance to add.

        Returns:
            tuple[bool, str]: (True, success message) if added, (False, message) if already exists.
        """
        if book.isbn in self.books:
            return False, f'Book with ISBN {book.isbn} already exists in the library.'

        self.books[book.isbn] = book
        return True, f'Successfully added: "{book.title}" by {book.author}'

    def remove_book(self, isbn: str) -> Tuple[bool, str]:
        """
        Removes a book by ISBN.

        Args:
            isbn: ISBN of the book to remove.

        Returns:
            tuple[bool, str]: (True, success message) if removed, (False, message) if not found.
        """
        if isbn in self.books:
            del self.books[isbn]
            return True, f'Removed book with ISBN {isbn}'
        return False, f'Book with ISBN {isbn} not found.'

    def get_book(self, isbn: str) -> Optional[Book]:
        """Retrieves a book by ISBN or None if not found."""
        return self.books.get(isbn)

    def list_books(self) -> List[Book]:
        """Returns a list of all books in the library."""
        return list(self.books.values())

    def __len__(self) -> int:
        return len(self.books)

    def __repr__(self) -> str:
        return f'Library(books={len(self)})'

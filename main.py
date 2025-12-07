'''Main application demonstrating the library system.'''

from book import Book
from library import Library


def main() -> None:
    """Runs the demonstration of adding books to the library."""
    lib = Library()

    demo_books = [
        ('1984', 'George Orwell', '978-0451524935'),
        ('To Kill a Mockingbird', 'Harper Lee', '978-0061120084'),
        ('The Great Gatsby', 'F. Scott Fitzgerald', '978-0743273565'),
    ]

    try:
        # Add books
        for title, author, isbn in demo_books:
            success, msg = lib.add_book(Book(title, author, isbn))
            print(msg)

        # Attempt duplicate
        success, msg = lib.add_book(Book(*demo_books[0]))
        print(msg)

        # List all books
        print('\nAll books in library:')
        for book in lib.list_books():
            print(f'  - {book}')

        print(f'\nTotal books: {len(lib)}')

        # Get specific book
        found = lib.get_book('978-0451524935')
        if found:
            print(f'Found: {found}')

        # Remove one
        success, msg = lib.remove_book('978-0061120084')
        print(msg)
        print(f'After removal, total books: {len(lib)}')

    except ValueError as e:
        print(f'Validation error: {e}')


if __name__ == '__main__':
    main()

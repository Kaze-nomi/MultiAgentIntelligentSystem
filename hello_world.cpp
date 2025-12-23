#include <iostream>

/**
 * @brief Main function that prints "Hello, World!" to the console.
 *
 * This is a simple C++ program demonstrating basic output.
 *
 * @return int Returns 0 on successful execution.
 */
int main() {
    try {
        // Print the hello world message
        std::cout << "Hello, World!" << std::endl;
        return 0;
    } catch (const std::exception& e) {
        // Handle any unexpected errors (though unlikely in this simple program)
        std::cerr << "An error occurred: " << e.what() << std::endl;
        return 1;
    }
}

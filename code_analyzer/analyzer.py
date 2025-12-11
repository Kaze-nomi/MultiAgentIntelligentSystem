import ast
from typing import Optional, Dict, Callable
from .models import ErrorInfo, AnalysisResult


class CodeAnalyzer:
    """Class for analyzing and fixing Python code.

    Example:
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_and_fix("def hello(): print('Hello')")
        if result.success:
            print(result.fixed_code)
    """

    # Standard indentation (4 spaces)
    INDENT_SIZE = 4
    INDENT_STR = ' ' * INDENT_SIZE

    def __init__(self):
        self.errors = []
        self._fix_strategies: Dict[str, Callable[[str, SyntaxError], Optional[str]]] = {
            "unexpected EOF while parsing": self._fix_eof_error,
        }
        # Note: IndentationError is a subclass of SyntaxError, so it will be caught there

    def analyze_and_fix(self, code: str) -> AnalysisResult:
        """Analyze the code for errors and attempt to fix them.

        Args:
            code (str): The Python code to analyze.

        Returns:
            AnalysisResult: The result of the analysis.

        Example:
            result = analyzer.analyze_and_fix("print('hello')")
            if not result.success:
                for error in result.errors:
                    print(error.message)
        """
        self.errors = []
        try:
            # Try to parse the code
            ast.parse(code)
            return AnalysisResult(errors=[], fixed_code=code, success=True)
        except SyntaxError as e:
            error_info = ErrorInfo(
                line=e.lineno if e.lineno else 0,
                column=e.offset if e.offset else None,
                message=str(e),
                error_type=type(e).__name__
            )
            self.errors.append(error_info)
            fixed_code = self._fix_syntax_error(code, e)
            return AnalysisResult(errors=self.errors, fixed_code=fixed_code, success=fixed_code is not None)
        except Exception as e:
            error_info = ErrorInfo(
                line=0,
                message=f"Unexpected error: {str(e)}",
                error_type=type(e).__name__
            )
            self.errors.append(error_info)
            return AnalysisResult(errors=self.errors, fixed_code=None, success=False)

    def _fix_syntax_error(self, code: str, error: SyntaxError) -> Optional[str]:
        """Attempt to fix common syntax errors.

        Args:
            code (str): The original code.
            error (SyntaxError): The syntax error.

        Returns:
            Optional[str]: Fixed code if possible, else None.

        Example:
            fixed = analyzer._fix_syntax_error("def func(): pass(", SyntaxError(...))
        """
        # Check if there's a strategy for this error message
        for key, strategy in self._fix_strategies.items():
            if key in error.msg:
                return strategy(code, error)

        # Handle IndentationError specifically
        if isinstance(error, IndentationError):
            return self._fix_indentation_error(code, error)

        # For other errors, return None (can't fix)
        return None

    def _fix_eof_error(self, code: str, error: SyntaxError) -> Optional[str]:
        """Fix unexpected EOF by balancing parentheses and brackets.

        Args:
            code (str): The original code.
            error (SyntaxError): The syntax error.

        Returns:
            Optional[str]: Fixed code if possible, else None.
        """
        # Count open parentheses and brackets
        open_parens = 0
        open_brackets = 0
        for char in code:
            if char == '(':
                open_parens += 1
            elif char == ')':
                open_parens -= 1
            elif char == '[':
                open_brackets += 1
            elif char == ']':
                open_brackets -= 1

        # Add missing closing ones at the end
        additions = ')' * max(0, open_parens) + ']' * max(0, open_brackets)
        if additions:
            return code + additions
        return None

    def _fix_indentation_error(self, code: str, error: SyntaxError) -> Optional[str]:
        """Fix indentation errors using AST to determine correct levels.

        Args:
            code (str): The original code.
            error (SyntaxError): The indentation error.

        Returns:
            Optional[str]: Fixed code if possible, else None.
        """
        lines = code.split('\n')
        if not error.lineno or error.lineno < 1 or error.lineno > len(lines):
            return None

        # Try to parse with adjusted indentation
        # Simple approach: increase indentation on the error line
        line_idx = error.lineno - 1
        line = lines[line_idx]
        if line.strip() and not line.startswith(' '):
            lines[line_idx] = self.INDENT_STR + line
            fixed_code = '\n'.join(lines)
            try:
                ast.parse(fixed_code)
                return fixed_code
            except SyntaxError:
                pass
        return None

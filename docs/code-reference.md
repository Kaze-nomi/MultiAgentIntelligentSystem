# Code Reference

## Table of Contents

- [Модуль code_analyzer/analyzer.py](#модуль-code_analyzeranalyzerpy)
  - [Описание модуля](#описание-модуля)
  - [Класс CodeAnalyzer](#класс-codeanalyzer)
    - [Константы](#константы)
    - [Метод __init__](#метод-__init__)
    - [Метод analyze_and_fix](#метод-analyze_and_fix)
    - [Метод _fix_syntax_error](#метод-_fix_syntax_error)
    - [Метод _fix_eof_error](#метод-_fix_eof_error)
    - [Метод _fix_indentation_error](#метод-_fix_indentation_error)

## Модуль code_analyzer/analyzer.py

### Описание модуля

Этот модуль содержит класс `CodeAnalyzer`, предназначенный для анализа и автоматического исправления распространенных синтаксических ошибок в Python коде. Модуль использует библиотеку `ast` для парсинга кода и предоставляет стратегии исправления для конкретных типов ошибок, таких как неожиданный конец файла (EOF) и ошибки отступов.

### Класс CodeAnalyzer

Класс для анализа и исправления Python кода.

#### Константы

- `INDENT_SIZE` (int): Стандартный размер отступа (4 пробела).
- `INDENT_STR` (str): Строка для отступа, состоящая из 4 пробелов.

#### Метод __init__

Инициализирует экземпляр класса.

**Параметры:**  
Нет параметров.

**Возвращает:**  
Нет возвращаемого значения.

**Пример использования:**

```python
analyzer = CodeAnalyzer()
```

#### Метод analyze_and_fix

Анализирует код на наличие ошибок и пытается их исправить.

**Параметры:**  
- `code` (str): Python код для анализа.

**Возвращает:**  
- `AnalysisResult`: Результат анализа, содержащий список ошибок, исправленный код и статус успеха.

**Пример использования:**

```python
analyzer = CodeAnalyzer()
result = analyzer.analyze_and_fix("def hello(): print('Hello')")
if result.success:
    print(result.fixed_code)
```

```python
result = analyzer.analyze_and_fix("print('hello')")
if not result.success:
    for error in result.errors:
        print(error.message)
```

#### Метод _fix_syntax_error

Пытается исправить распространенные синтаксические ошибки.

**Параметры:**  
- `code` (str): Исходный код.
- `error` (SyntaxError): Синтаксическая ошибка.

**Возвращает:**  
- `Optional[str]`: Исправленный код, если возможно, иначе None.

**Пример использования:**

```python
fixed = analyzer._fix_syntax_error("def func(): pass(", SyntaxError(...))
```

#### Метод _fix_eof_error

Исправляет неожиданный конец файла путем балансировки скобок и квадратных скобок.

**Параметры:**  
- `code` (str): Исходный код.
- `error` (SyntaxError): Синтаксическая ошибка.

**Возвращает:**  
- `Optional[str]`: Исправленный код, если возможно, иначе None.

#### Метод _fix_indentation_error

Исправляет ошибки отступов с использованием AST для определения правильных уровней.

**Параметры:**  
- `code` (str): Исходный код.
- `error` (SyntaxError): Ошибка отступа.

**Возвращает:**  
- `Optional[str]`: Исправленный код, если возможно, иначе None.
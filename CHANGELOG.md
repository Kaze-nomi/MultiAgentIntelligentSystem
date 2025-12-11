# Changelog
    All notable changes to this project will be documented in this file.

    The format is based on Keep a Changelog,
    and this project adheres to Semantic Versioning.

    ## [0.2.0] - 2025-12-11

### Added

- **music_composer_agent**: Created new constants.py file for constants to improve maintainability.

### Changed

- **music_composer_agent**: Renamed MusicalCompositionModel to MusicalComposition and updated imports in __init__.py.
- **music_composer_agent**: Renamed class to MusicalComposition, optimized add_note method to avoid full validation, and completed to_dict method in models.py.
- **music_composer_agent**: Added aiohttp import, updated model import, and added comment for user authentication in server.py.
- **music_composer_agent**: Updated generate_composition to async, added key parameter with default, added raises, and updated import in interfaces.py.
- **music_composer_agent**: Moved VALID_KEYS and VALID_STYLES to constants.py, enhanced input sanitization with length limit and character filtering, added try-except for KeyError, completed required keys check, and added basic type validation for notes in services.py.
- **tests**: Updated imports and class names in test_music_composer_agent.py.

### Fixed

- **tests**: Fixed test for async generate_composition in test_music_composer_agent.py.


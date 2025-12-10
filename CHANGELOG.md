# Changelog
    All notable changes to this project will be documented in this file.

    The format is based on Keep a Changelog,
    and this project adheres to Semantic Versioning.

    ## [0.1.0] - 2025-12-10

### Added

- **src/agents/music_synthesizer_agent**: MusicSynthesizerAgent для синтеза музыки: поддержка raw PCM (без WAV-заголовка), исправленный расчёт длительности, атомарный экспорт во временные файлы с очисткой при ошибках, лимиты max_length/max_items в моделях (Pydantic v2), per-user ограничения хранения (10 файлов, 100MB) с уникальными именами (UUID), полная реализация стратегий, агента и сервера с обработкой лимитов через HTTP 400.


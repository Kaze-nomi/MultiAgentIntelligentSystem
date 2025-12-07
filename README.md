// model : tngtech/deepseek-r1t-chimera:free

// model : deepseek/deepseek-chat-v3-0324

//6487984216


const formData = $('📋 Prepare Data').first().json;
const treeResponse = $input.first().json;

// Парсим структуру репозитория
const structure = (treeResponse.tree || []).map(item => ({
  path: item.path,
  type: item.type === 'blob' ? 'file' : 'dir',
  size: item.size || 0,
  sha: item.sha
}));

// РАСШИРЕННЫЕ паттерны для ключевых файлов
const keyPatterns = [
  // ===== Конфигурационные файлы =====
  /^readme\.md$/i,
  /^changelog\.md$/i,
  /^contributing\.md$/i,
  /^package\.json$/,
  /^package-lock\.json$/,
  /^requirements\.txt$/,
  /^pyproject\.toml$/,
  /^setup\.py$/,
  /^setup\.cfg$/,
  /^poetry\.lock$/,
  /^Pipfile$/,
  /^docker-compose\.ya?ml$/,
  /^dockerfile$/i,
  /^\.env\.example$/,
  /^\.env\.sample$/,
  /^tsconfig\.json$/,
  /^vite\.config\.(js|ts)$/,
  /^webpack\.config\.js$/,
  /^next\.config\.(js|mjs)$/,
  /^nuxt\.config\.(js|ts)$/,
  /^\.eslintrc(\.(js|json|yml))?$/,
  /^\.prettierrc(\.(js|json|yml))?$/,
  /^tailwind\.config\.(js|ts)$/,
  /^cargo\.toml$/i,
  /^go\.mod$/,
  /^go\.sum$/,
  /^makefile$/i,
  /^justfile$/i,
  
  // ===== Точки входа =====
  /^main\.(py|js|ts|go|rs)$/,
  /^index\.(py|js|ts|tsx|jsx)$/,
  /^app\.(py|js|ts|tsx|jsx)$/,
  /^server\.(py|js|ts)$/,
  /^run\.(py|js|ts)$/,
  /^cli\.(py|js|ts)$/,
  
  // ===== Python файлы =====
  /\.py$/,  // Все Python файлы
  
  // ===== JavaScript/TypeScript =====
  /^src\/.*\.(js|jsx|ts|tsx)$/,
  /^lib\/.*\.(js|jsx|ts|tsx)$/,
  /^app\/.*\.(js|jsx|ts|tsx)$/,
  /^pages\/.*\.(js|jsx|ts|tsx)$/,
  /^components\/.*\.(js|jsx|ts|tsx)$/,
  /^hooks\/.*\.(js|jsx|ts|tsx)$/,
  /^utils\/.*\.(js|ts)$/,
  /^helpers\/.*\.(js|ts)$/,
  /^services\/.*\.(js|ts)$/,
  /^api\/.*\.(js|ts)$/,
  /^routes?\/.*\.(js|ts)$/,
  /^controllers?\/.*\.(js|ts)$/,
  /^middleware\/.*\.(js|ts)$/,
  /^models?\/.*\.(js|ts)$/,
  /^schemas?\/.*\.(js|ts)$/,
  /^types?\/.*\.(ts|d\.ts)$/,
  /^store\/.*\.(js|ts)$/,
  /^config\/.*\.(js|ts|json)$/,
  
  // ===== Go =====
  /\.go$/,
  
  // ===== Rust =====
  /\.rs$/,
  
  // ===== C++ =====
  /\.cpp$/,  
  /\.cxx$/,  
  /\.c$/,  

  // ===== Java =====
  /\.java$/,
  /\build.gradle.kts$/,
  /\pom.xml$/,

  
  // ===== Конфиги в поддиректориях =====
  /config\/.*\.(json|ya?ml|toml)$/,
  /\.github\/workflows\/.*\.ya?ml$/
];

// Паттерны для ИСКЛЮЧЕНИЯ
const excludePatterns = [
  /node_modules\//,
  /\.git\//,
  /dist\//,
  /build\//,
  /\.next\//,
  /\.nuxt\//,
  /out\//,
  /__pycache__\//,
  /\.pytest_cache\//,
  /\.mypy_cache\//,
  /\.ruff_cache\//,
  /\.venv\//,
  /venv\//,
  /\.env\//,
  /env\//,
  /virtualenv\//,
  /\.tox\//,
  /\.eggs\//,
  /\.egg-info\//,
  /htmlcov\//,
  /coverage\//,
  /\.coverage/,
  /\.cache\//,
  /\.temp\//,
  /\.tmp\//,
  /target\//,  // Rust/Java build
  /vendor\//,  // Go vendor
  /\.idea\//,
  /\.vscode\//,
  /\.DS_Store/,
  /Thumbs\.db/,
  /\.log$/,
  /\.lock$/,  // Кроме package-lock.json и poetry.lock
  /\.min\.(js|css)$/,  // Минифицированные файлы
  /\.map$/,  // Source maps
  /\.bundle\.(js|css)$/,
  /test_.*\.py$/,  // Тестовые файлы Python
  /.*_test\.py$/,
  /.*\.test\.(js|ts|jsx|tsx)$/,  // Тестовые файлы JS
  /.*\.spec\.(js|ts|jsx|tsx)$/,
  /__tests__\//,
  /tests?\//,  // Директории с тестами
  /\.d\.ts$/,  // TypeScript декларации (обычно генерируются)
];

// Приоритетные файлы (загружаем первыми)
const priorityPatterns = [
  /^readme\.md$/i,
  /^package\.json$/,
  /^requirements\.txt$/,
  /^pyproject\.toml$/,
  /^main\.(py|js|ts)$/,
  /^index\.(py|js|ts)$/,
  /^app\.(py|js|ts)$/,
  /^server\.(py|js|ts)$/,
  /models?\.py$/,
  /schema\.py$/,
];

// Фильтруем файлы
const allFiles = structure.filter(item => {
  // Только файлы
  if (item.type !== 'file') return false;
  
  // Ограничение размера (100KB)
  if (item.size > 100000) return false;
  
  // Проверяем исключения
  if (excludePatterns.some(p => p.test(item.path))) {
    // Исключение для package-lock.json и poetry.lock
    if (item.path === 'package-lock.json' || item.path === 'poetry.lock') {
      return false; // Всё равно исключаем - слишком большие
    }
    return false;
  }
  
  // Проверяем совпадение с ключевыми паттернами
  return keyPatterns.some(p => p.test(item.path));
});

// Сортируем: приоритетные файлы первыми
const sortedFiles = allFiles.sort((a, b) => {
  const aPriority = priorityPatterns.some(p => p.test(a.path)) ? 0 : 1;
  const bPriority = priorityPatterns.some(p => p.test(b.path)) ? 0 : 1;
  
  if (aPriority !== bPriority) {
    return aPriority - bPriority;
  }
  
  // При равном приоритете - меньшие файлы первыми
  return a.size - b.size;
});

// Берём топ-50 файлов
const filesToFetch = sortedFiles.slice(0, 50);

// Сохраняем SHA для ВСЕХ файлов (для UPDATE операций)
const existingFileShas = {};
structure.forEach(item => {
  if (item.type === 'file') {
    existingFileShas[item.path] = item.sha;
  }
});

// Логируем для отладки
console.log(`Total files in repo: ${structure.filter(i => i.type === 'file').length}`);
console.log(`Files matching patterns: ${allFiles.length}`);
console.log(`Files to fetch: ${filesToFetch.length}`);
console.log(`First 10 files:`, filesToFetch.slice(0, 10).map(f => f.path));

return [{
  json: {
    ...formData,
    structure: structure,
    files_to_fetch: filesToFetch,
    existing_file_shas: existingFileShas,
    stats: {
      total_files: structure.filter(i => i.type === 'file').length,
      matching_files: allFiles.length,
      files_to_fetch: filesToFetch.length
    }
  }
}];
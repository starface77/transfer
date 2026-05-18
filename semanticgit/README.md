# s-git: Semantic Git

**s-git** — система контроля версий, которая отслеживает *смысл* кода, а не буквы.

Вместо текстовых diff-ов s-git анализирует AST (абстрактное синтаксическое дерево) и показывает семантические изменения: какие функции добавлены, какие классы изменены, что было переименовано или перемещено.

## Ключевые возможности

| Возможность | Описание |
|---|---|
| **Семантический diff** | `sgit diff` показывает: "Функция `compute_discount` перенесена в класс `BillingManager`" вместо "удалена строка 15, добавлена строка 89" |
| **Автокоммиты** | `sgit commit` автоматически генерирует осмысленные сообщения на основе семантической дельты |
| **Семантическое слияние** | `sgit merge` анализирует смысл изменений и автоматически сливает неконфликтующие правки |
| **AST-хранилище** | Каждый коммит хранит семантический граф проекта, а не текстовые файлы |
| **Обнаружение переименований** | Система распознаёт переименования функций и перемещения между классами |

## Быстрый старт

```bash
pip install -e .

# Инициализация
sgit init

# Добавить файлы и создать коммит
sgit add .
sgit commit

# Посмотреть семантический diff
sgit diff

# История коммитов
sgit log

# Статус
sgit status

# Ветвление и слияние
sgit branch feature
sgit checkout feature
# ... правки ...
sgit checkout main
sgit merge feature
```

## Пример семантического diff-а

```text
Semantic diff:
  billing.py:
    ~ Modified method 'Service.process'
      signature changed: (self, data) -> (self, data, timeout=...)
    + Added class 'BillingManager'
    - Removed function 'compute_discount'
    >> Moved 'compute_discount' from (module) to BillingManager
```

## Пример автокоммита

```text
[main a1b2c3d4] Add 3 elements; Update 1 element; Move 1 element

Added:
  + class 'BillingManager'
  + method 'BillingManager.compute_discount'
  + import 'logging'
Modified:
  ~ method 'Service.process' (signature changed)
Moved:
  >> 'compute_discount' from (module) to BillingManager

Affected 1 file: billing.py
```

## Архитектура

```text
s-git/
├── src/sgit/
│   ├── cli.py          # Click CLI
│   ├── models.py       # SemanticNode, FileSnapshot, Commit, SemanticDelta
│   ├── ast_parser.py   # Python AST → семантическое дерево
│   ├── diff_engine.py  # Семантический diff
│   ├── merge_engine.py # Трёхстороннее семантическое слияние
│   ├── commit_gen.py   # Автогенерация сообщений коммитов
│   └── storage.py      # .sgit хранилище (объекты, коммиты, ветки)
├── tests/
└── pyproject.toml
```

## Как это работает

1. **AST-парсинг**: Каждый `.py` файл преобразуется в дерево семантических узлов (функции, классы, методы, импорты, переменные).
2. **Семантическое хэширование**: Каждый узел получает хэш на основе своей структуры и содержимого.
3. **Дельта-анализ**: При `sgit diff` система сравнивает деревья двух версий, находит добавления, удаления, модификации, переименования и перемещения.
4. **Автокоммиты**: На основе дельты генерируется человеко-читаемое описание изменений.
5. **Семантическое слияние**: При `sgit merge` трёхсторонний анализ определяет, конфликтуют ли изменения семантически, и автоматически сливает неконфликтующие правки.

## Тесты

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Лицензия

MIT

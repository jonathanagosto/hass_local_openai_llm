# AGENTS.md

Hard-earned context for AI-driven development of the `local_openai` HACS integration.

## Repo layout

- `custom_components/local_openai/` — integration code.
  - `__init__.py` — entry point: creates `AsyncOpenAI` client, registers `local_openai.add_to_weaviate`, and runs config-entry migrations.
  - `config_flow.py` — main config + subentries (`conversation`, `ai_task_data`).
  - `entity.py` — shared `LocalAiEntity` base: streaming, tool/RAG handling, message conversion.
  - `conversation.py` / `ai_task.py` — platform setup; lazy-import dispatch to server-specific entity classes.
  - `entities/` — server-specific behavior (`deepseek`, `llama_cpp`).
- `tests/` — pytest suite.
- `weaviate/` — docker-compose + NodeJS data manager for optional RAG.

## AI development workflow

1. Identify the scope: base logic, existing server-specific behavior, or new server type.
2. Inspect the dispatch maps in `conversation.py` and `ai_task.py` and the relevant `entities/*.py` file.
3. Add or update focused tests before/while changing logic.
4. Run targeted tests first, then the full suite.
5. Run the exact verification order below.
6. Stop and summarize the diff for human review before pushing/versioning.

## Exact verification order

```bash
# 1. auto-format
ruff format .

# 2. lint
ruff check .

# 3. typecheck
mypy custom_components/local_openai

# 4. tests
pytest tests/
```

Focused examples:

```bash
pytest tests/entities/llama_cpp/test_model_alias.py -v
pytest tests/entities/llama_cpp/ -v
```

## Test gotchas

- `tests/conftest.py` mocks `turbojpeg` **before** any Home Assistant imports. Preserve this import order in every new test module.
- Fixtures manually create `ConfigEntry` / `ConfigSubentry` and inject them into `hass.config_entries._entries` / `entry._subentries`.
- Tests are pinned to `homeassistant==2026.5.0` and use the `pytest-homeassistant-custom-component` harness.

## Architecture notes

- Not a pip package; loaded by HA as a custom component. No `setup.py`.
- Entry point: `__init__.py` creates `AsyncOpenAI` client and stores it in `entry.runtime_data`.
- Config flow uses subentries (`conversation`, `ai_task_data`) so each agent/model has its own subentry under one server config entry.
- Platforms dispatch to server-specific entity classes via lazy import maps in `conversation.py` and `ai_task.py`.
- Server type `generic` falls back to `LocalAiConversationEntity` / `LocalAITaskEntity`.
- `entities/deepseek.py` and `entities/llama_cpp.py` import from `conversation.py` and `ai_task.py`; avoid circular imports and keep server imports lazy in the platform maps.
- Server-specific behavior should be added by subclassing `LocalAiEntity` and overriding `_get_extra_body_args()` and/or `_convert_content_to_chat_message()`, not by special-casing in `entity.py`.
- `async_migrate_entry` renames `Name`→`Key` in `chat_template_opts.chat_template_kwargs` when migrating from entry version 1 to 2.

## How to add or modify a server type

1. Add constants in `const.py` and include the display name in `SERVER_TYPE_OPTIONS` if it should appear in the initial config flow.
2. Create `entities/<server>.py` with:
   - `get_conversation_config_schema()`
   - `get_ai_task_config_schema()`
   - entity classes subclassing `LocalAiConversationEntity` / `LocalAITaskEntity`
3. Wire them into the lazy maps in `conversation.py` and `ai_task.py`.
4. Add schema and config-key resolution in `config_flow.py` via `_get_conversation_config_schema`, `_get_ai_task_config_schema`, and `_get_server_type_config_key`.
5. Add tests under `tests/entities/<server>/`.

## Human-in-the-loop checkpoints

STOP and ask for explicit human approval before committing any change to:

- `manifest.json`: version, dependencies, minimum HA.
- `hacs.json`: homeassistant version, release metadata.
- `__init__.py`: config entry `VERSION` or `async_migrate_entry`.
- `services.yaml`: new service actions or schema fields.
- `requirements_test.txt`: dependency bumps or additions.
- Translation strings in `translations/en.json`.
- New server types or renames of existing config keys.
- `_transform_stream` thinking/reasoning tag handling (high regression risk).
- Release zip / tag creation (HACS builds `local_openai.zip` from GitHub releases).

## Style / lint

- `ruff` selects `ALL` with specific ignores (see `.ruff.toml`). Tests inherit parent config plus per-file ignores from `tests/.ruff.toml`.
- `mypy` strict: `disallow_untyped_defs`, `disallow_untyped_calls`, etc.
- Max complexity 25 per `ruff.toml`.

## Dependencies

- Runtime: `openai>=2.21.0`, `demoji>=1.1.0` (manifest.json).
- Minimum HA: `2025.8` (hacs.json); tests pin `2026.5.0`.

## Release / packaging

- `hacs.json`: `zip_release: true`, `filename: "local_openai.zip"`.
- There is no CI, pre-commit, or release script in the repo today; releases are manual.

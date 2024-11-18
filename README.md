# Conventional Emojis 🎨

A [pre-commit](https://pre-commit.com/) hook that enhances your conventional commits with customizable emojis based on commit type, scope, or their combinations.

## Features

- ✨ Validates conventional commit format
- 🎯 Adds emojis based on commit type
- 🔍 Supports scope-based emojis
- 🔄 Handles type-scope combinations
- ⚡ Customizable commit message template
- 💥 Breaking changes indicator

## Conventional Commit Syntax

See [Conventional Commits specification](https://www.conventionalcommits.org/en/v1.0.0/) for full specification:

```text
<type>[optional scope]: <description>
```

### Example

Given the commit message:

```bash
feat(parser): add ability to parse arrays
```

With this hook, it will be transformed to:

```bash
feat(parser): ✨ add ability to parse arrays
```

## Installation

1. Install `pre-commit` (see [pre-commit documentation](https://pre-commit.com/)):

    ```bash
    pip install pre-commit
    ```

2. Add the following configuration to your `.pre-commit-config.yaml` file:

    ```yaml
    repos:
      - repo: https://github.com/pschonev/conventional-emojis
        rev: v0.1.0
        hooks:
          - id: conventional-emojis
    ```

3. Install the pre-commit hooks:

    ```bash
    pre-commit install
    ```

## Configuration

### Basic Configuration

The default configuration can be found in [`conventional_emojis/constants.py`](conventional_emojis/constants.py):

```python
COMMIT_TYPES: dict[str, str] = {
    "feat": "✨",
    "fix": "🐛",
    "docs": "📝",
    "style": "💄",
    "refactor": "♻️",
    "perf": "⚡️",
    "test": "✅",
    "build": "🏗️",
    "ci": "👷",
    "config": "🔧",
    "chore": "🧹",
    "wip": "🚧",
}
BREAKING: str = "💥"
COMMIT_MESSAGE_TEMPLATE = "{conventional_prefix} {breaking_emoji}{type_emoji}{scope_emoji} {description}\n{body}"
```

To overwrite the default configuration, create a [`conventional_emojis_config.toml`](conventional_emojis_config.toml) file in your project root:

```toml
[types]
feat = "🚀"
fix = "🔧"
chore = "🧹"

[scopes]
api = "🔌"
ui = "🎨"

[combos.feat]
"api.*" = "🐍"
ui = "🖥️"

[combos.chore]
"catch|except.*|error" = "🥅"

[config]
breaking_emoji = "💣"
commit_message_template = "{breaking_emoji}{type_emoji}{scope_emoji} {conventional_prefix}: {description}\n\n{body}"
```

### Config

#### 1. Basic Type Emojis

Defining existing types in the config will overwrite default ones. Only types that exist as defaults or that are newly added in the config are valid and accepted by the pre-commit hook.

```toml
[types]
feat = "🍕"
release = "🚀"
```

Overwriting existing type:

```bash
fix: fix annoying bug ---> fix: 🍕 fix annoying bug
```

Adding a new type:

```bash
release: release awesome feature ---> release: 🚀 release awesome feature
```

#### 2. Scope Emojis

Scopes can be defined in the config and will add an **additional** emoji to the commit message. Scopes are defined as regex patterns.

Note that by default all types can also be used as scopes and will add their respective emojis as a scope-emoji (can be disabled with `--disable-types-as-scopes`).

Just like types, you can also enforce that the scope has a matching pattern defined in the config using the option `--enforce-scope-patterns`.

```toml
[types]
feat = "✨"
chore = "🧹"

[scopes]
db = "📦"
"api|code" = "🔌"
"g?ui" = "🎨"
```

```bash
feat(api): new endpoint --->  feat(api): ✨🔌 new endpoint
```

#### 3. Type-Scope Combinations

Each type can optionally have **combo** definitions. If a type-scope combo is detected, the emojis for the type and scope are **not** used and instead the combo-emoji is used (in the position of the *type-emoji*). Just like before, scopes are defined as regex patterns.

```toml
[types]
feat = "✨"
chore = "🧹"

[combos.feat]
api = "🐍"

[combos.chore]
"g?ui" = "🖌️"
"lint.*" = "☝️🤓"
```

```bash
feat(api): add new API feature ----> feat(api): 🐍 add new API feature

chore(gui): update button ----> chore(gui): 🖌️ update button

chore(linting): fix linting issue ---->  chore(linting): ☝️🤓 fix linting issue
```

#### 4. Breaking Changes

By default, a breaking change (indicated by a ! before the :) adds an additional breaking-emoji. This emoji can be changed in the config or disabled via the `--disable-breaking-emoji` option.

```toml
[config]
breaking_emoji = "🎉"
```

```bash
feat!: breaking change ----> feat!: 🎉✨ breaking change
```

### Available Options

- `--config-file`: Path to custom config file (default: `conventional_emojis_config.toml`)
- `--disable-types-as-scopes`: Prevent using commit types as valid scopes
- `--enforce-scope-patterns`: Require scopes to match defined patterns
- `--disable-breaking-emoji`: Don't show breaking change emoji
- `--template`: Override commit message template

## Template Format

The template must **only** contain the following placeholders (all of which are optional):

- `{breaking_emoji}`: Breaking change emoji
- `{type_emoji}`: Commit type emoji
- `{scope_emoji}`: Scope emoji
- `{conventional_prefix}`: Original conventional commit prefix (including the semicolon)
- `{description}`: Commit message description (everything before newline)
- `{body}`: Commit message body

## Error Handling

The hook will fail with helpful error messages when:

- Commit message doesn't follow conventional commit format
- Undefined commit type is used
- Undefined scope is used (when `--enforce-scope-patterns` is enabled)
- Invalid template format is provided (it contains unknown placeholders)

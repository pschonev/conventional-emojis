#!/usr/bin/env python3

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import msgspec

from conventional_emojis.constants import (
    BASE_PATTERN,
    BREAKING,
    COMMIT_MESSAGE_TEMPLATE,
    COMMIT_TYPES,
)
from conventional_emojis.exceptions import (
    InvalidCommitTemplateError,
    NoConventionalCommitTypeFoundError,
    NonConventionalCommitError,
    UndefinedScopeError,
)


@dataclass
class CommitMessageDetails:
    conventional_prefix: str
    description: str
    body: str
    commit_type: str
    scope: str
    breaking: bool


class ConventionalEmojisConfig(msgspec.Struct, forbid_unknown_fields=True):
    types: dict[str, str] = msgspec.field(
        default_factory=lambda: dict(COMMIT_TYPES),
    )
    scopes: dict[str, str] | None = None
    combos: dict[str, dict[str, str]] | None = None
    breaking_emoji: str = BREAKING
    commit_message_template: str = COMMIT_MESSAGE_TEMPLATE

    @classmethod
    def from_toml(
        cls,
        config_file: Path,
        *,
        allow_types_as_scopes: bool = True,
        template_override: str | None = None,
        default_commit_types: dict[str, str] = COMMIT_TYPES,
    ) -> "ConventionalEmojisConfig":
        """Load configuration from TOML file with proper defaults and overrides."""
        if config_file.exists():
            with config_file.open("rb") as f:
                try:
                    instance = msgspec.toml.decode(f.read(), type=cls)
                except msgspec.ValidationError as e:
                    msg = f"Error parsing custom rules TOML file: {e}"
                    raise msgspec.ValidationError(msg) from None
                # Create a new dict with defaults and update with config types
                types = dict(default_commit_types)
                types.update(instance.types)
                instance.types = types
        else:
            print("No custom rules TOML file found.")
            instance = cls(types=default_commit_types)

        # Apply template override if provided
        if template_override is not None:
            instance.commit_message_template = template_override

        # Update scopes with types if allowed
        if instance.scopes is not None and allow_types_as_scopes:
            instance.scopes.update(instance.types)

        return instance


@dataclass
class Emojis:
    type_emoji: str
    scope_emoji: str
    breaking_emoji: str


def extract_commit_details(
    commit_message: str,
    base_pattern: str = BASE_PATTERN,
) -> CommitMessageDetails:
    lines = commit_message.split("\n")
    title = lines[0]

    if not (match := re.match(base_pattern, title)):
        raise NonConventionalCommitError

    # Extract the conventional prefix and description from the title
    conventional_prefix = title[: match.end()].strip()
    description = title[match.end() :].strip()

    # Extract the body from the rest of the lines
    body = "\n".join(lines[1:]).strip()

    return CommitMessageDetails(
        conventional_prefix=conventional_prefix,
        description=description,
        body=body,
        commit_type=match.group("type"),
        scope=match.group("scope") if match.group("scope") else "",  # Handle None scope
        breaking=bool(match.group("breaking")),
    )


def get_emojis(
    details: CommitMessageDetails,
    mappings: ConventionalEmojisConfig,
    *,
    enforce_scope_patterns: bool = False,
    disable_breaking_emoji: bool = False,
) -> Emojis:
    # First check for combos
    if (
        mappings.combos
        and details.scope
        and (combo_patterns := mappings.combos.get(details.commit_type)) is not None
    ):
        for pattern, emoji in combo_patterns.items():
            if re.fullmatch(pattern, details.scope.strip()):
                # If we find a matching combo, use its emoji as the type_emoji
                # and set scope_emoji to empty string
                return Emojis(
                    type_emoji=emoji,
                    scope_emoji="",
                    breaking_emoji=mappings.breaking_emoji
                    if details.breaking and not disable_breaking_emoji
                    else "",
                )

    # If no combo matches, proceed with regular type and scope emoji logic
    if (type_emoji := mappings.types.get(details.commit_type)) is None:
        msg = (
            f"Commit type '{details.commit_type}' does not have a corresponding emoji.\n"
            f"Available types are: {', '.join(sorted(mappings.types.keys()))}"
        )
        raise NoConventionalCommitTypeFoundError(msg)

    scope_emoji = ""
    if details.scope and mappings.scopes is not None:
        for pattern, emoji in mappings.scopes.items():
            if re.fullmatch(pattern, details.scope.strip()):
                scope_emoji = emoji
                break
        else:  # no break - no matching pattern found
            if enforce_scope_patterns:
                msg = f"Scope '{details.scope}' does not match any defined patterns in the configuration."
                raise UndefinedScopeError(msg)

    return Emojis(
        type_emoji=type_emoji,
        scope_emoji=scope_emoji,
        breaking_emoji=mappings.breaking_emoji
        if details.breaking and not disable_breaking_emoji
        else "",
    )


def update_commit_message(
    details: CommitMessageDetails,
    emojis: Emojis,
    commit_template: str,
) -> str:
    try:
        return commit_template.format(
            conventional_prefix=details.conventional_prefix,
            description=details.description,
            breaking_emoji=emojis.breaking_emoji,
            type_emoji=emojis.type_emoji,
            scope_emoji=emojis.scope_emoji,
            body=details.body,
        )
    except KeyError as e:
        msg = f"""Invalid commit template {commit_template}.
        Not all required fields are present: conventional_prefix, description, breaking_emoji, type_emoji, scope_emoji, body."""
        raise InvalidCommitTemplateError(msg) from e


def process_commit_message(
    commit_message: str,
    config: ConventionalEmojisConfig,
    *,
    enforce_scope_patterns: bool = False,
    disable_breaking_emoji: bool = False,
) -> str:
    details = extract_commit_details(commit_message)
    emojis = get_emojis(
        details,
        config,
        enforce_scope_patterns=enforce_scope_patterns,
        disable_breaking_emoji=disable_breaking_emoji,
    )
    return update_commit_message(details, emojis, config.commit_message_template)


def process_conventional_commit(
    commit_message_file: Path,
    *,
    allow_types_as_scopes: bool,
    config_file: Path = Path("conventional_emojis_config.yaml"),
    template: str | None = None,
    enforce_scope_patterns: bool = False,
    disable_breaking_emoji: bool = False,
) -> None:
    config = ConventionalEmojisConfig.from_toml(
        config_file=config_file,
        allow_types_as_scopes=allow_types_as_scopes,
        template_override=template,
    )

    with commit_message_file.open("r") as file:
        commit_message = file.read().strip()

    try:
        processed_message = process_commit_message(
            commit_message,
            config,
            enforce_scope_patterns=enforce_scope_patterns,
            disable_breaking_emoji=disable_breaking_emoji,
        )
        with commit_message_file.open("w") as file:
            file.write(processed_message)
        print(
            "🎉 Commit message follows Conventional Commits rules and has been updated with an emoji.",
        )
        sys.exit(0)
    except (
        NonConventionalCommitError,
        NoConventionalCommitTypeFoundError,
        UndefinedScopeError,
    ) as e:
        print(f"💥 Commit message: '{commit_message}'\n💥 {e}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process commit messages and add emojis.",
    )
    parser.add_argument(
        "commit_message_file",
        type=Path,
        help="Path to the commit message file",
    )
    parser.add_argument(
        "--config-file",
        type=Path,
        default=Path("conventional_emojis_config.toml"),
        help="Path to the configuration file",
    )
    parser.add_argument(
        "--disable-types-as-scopes",
        action="store_true",
        help="Disable using types as scopes in commit messages",
    )
    parser.add_argument(
        "--template",
        type=str,
        help="Override commit message template (overrides both default and config file settings)",
    )
    parser.add_argument(
        "--disable-breaking-emoji",
        action="store_true",
        help="Disable showing breaking change emoji",
    )
    parser.add_argument(
        "--enforce-scope-patterns",
        action="store_true",
        help="Enforce scope to match defined patterns in settings",
    )
    args = parser.parse_args()

    process_conventional_commit(
        commit_message_file=args.commit_message_file,
        allow_types_as_scopes=not args.disable_types_as_scopes,
        config_file=args.config_file,
        template=args.template,
        enforce_scope_patterns=args.enforce_scope_patterns,
        disable_breaking_emoji=args.disable_breaking_emoji,
    )


if __name__ == "__main__":
    main()

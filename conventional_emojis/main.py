#!/usr/bin/env python3
import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from conventional_emojis.constants import BASE_PATTERN, BREAKING, COMMIT_TYPES
from conventional_emojis.exceptions import (
    NoConventionalCommitTypeFoundError,
    NonConventionalCommitError,
)


@dataclass
class CommitMessageDetails:
    title: str
    body: str
    commit_type: str
    scope: str
    breaking: bool
    match_end: int


@dataclass
class EmojiMappings:
    commit_types: dict[str, str]
    scopes: dict[str, str]
    breaking_emoji: str


def extract_commit_details(
    commit_message: str,
    base_pattern: str = BASE_PATTERN,
) -> CommitMessageDetails:
    lines = commit_message.split("\n")
    title = lines[0]

    if not (match := re.match(base_pattern, title)):
        raise NonConventionalCommitError

    return CommitMessageDetails(
        title=title,
        body="\n".join(lines[1:]),
        commit_type=match.group("type"),
        scope=match.group("scope"),
        breaking=bool(match.group("breaking")),
        match_end=match.end(),
    )


def set_emojis(details: CommitMessageDetails, mappings: EmojiMappings) -> str:
    if (type_emoji := mappings.commit_types.get(details.commit_type)) is None:
        msg = (
            f"Commit type '{details.commit_type}' does not have a corresponding emoji."
        )
        raise NoConventionalCommitTypeFoundError(msg)
    scope_emoji = mappings.scopes.get(details.scope, "") if details.scope else ""
    return f"{mappings.breaking_emoji if details.breaking else ''}{type_emoji}{scope_emoji}"


def update_commit_message(details: CommitMessageDetails, emojis: str) -> str:
    updated_title = f"{details.title[:details.match_end].strip()} {emojis} {details.title[details.match_end:].strip()}"
    return f"{updated_title}\n{details.body}"


def process_commit_message(commit_message: str, mappings: EmojiMappings) -> str:
    details = extract_commit_details(commit_message)
    emojis = set_emojis(details, mappings)
    return update_commit_message(details, emojis)


def load_yaml_config(config_file: Path) -> dict:
    if not config_file.exists():
        print("No custom rules YAML file found.")
        return {}
    with config_file.open("r") as file:
        return yaml.safe_load(file)


def parse_config(
    config_data: dict,
    *,
    allow_types_as_scopes: bool,
    breaking_emoji: str = BREAKING,
    commit_types: dict[str, str] = COMMIT_TYPES,
) -> EmojiMappings:
    scopes = config_data.get("scopes", {})
    if allow_types_as_scopes:
        scopes.update(commit_types)

    commit_types.update(config_data.get("types", {}))

    return EmojiMappings(
        commit_types,
        scopes,
        config_data.get("breaking", breaking_emoji),
    )


def process_conventional_commit(
    commit_message_file: Path,
    *,
    allow_types_as_scopes: bool,
    config_file: Path = Path("conventional_emojis_config.yaml"),
) -> None:
    config_data = load_yaml_config(config_file)
    mappings = parse_config(config_data, allow_types_as_scopes=allow_types_as_scopes)

    with commit_message_file.open("r") as file:
        commit_message = file.read().strip()

    try:
        processed_message = process_commit_message(commit_message, mappings)
        with commit_message_file.open("w") as file:
            file.write(processed_message)
        print(
            "🎉 Commit message follows Conventional Commits rules and has been updated with an emoji.",
        )
        sys.exit(0)
    except (NonConventionalCommitError, NoConventionalCommitTypeFoundError) as e:
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
        default=Path("conventional_emojis_config.yaml"),
        help="Path to the configuration file",
    )
    parser.add_argument(
        "--disable-types-as-scopes",
        action="store_true",
        help="Disable using types as scopes in commit messages",
    )
    args = parser.parse_args()

    process_conventional_commit(
        commit_message_file=args.commit_message_file,
        allow_types_as_scopes=not args.disable_types_as_scopes,
        config_file=args.config_file,
    )


if __name__ == "__main__":
    main()

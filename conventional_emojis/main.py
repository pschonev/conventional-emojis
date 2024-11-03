#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path

import yaml

from conventional_emojis.constants import BASE_PATTERN, BREAKING, COMMIT_TYPES
from conventional_emojis.exceptions import (
    NoConventionalCommitTypeFoundError,
    NonConventionalCommitError,
)


def load_custom_rules(
    config_file: Path = Path("conventional_emojis_config.yaml"),
) -> tuple[dict[str, str], dict[str, str], str]:
    if not config_file.exists():
        print("No custom rules YAML file found.")
        return COMMIT_TYPES, {}, BREAKING

    with config_file.open("r") as file:
        config_data = yaml.safe_load(file)

    COMMIT_TYPES.update(config_data.get("types", {}))
    scopes = config_data.get("scopes", {})

    breaking_emoji = config_data.get("breaking", BREAKING)

    return COMMIT_TYPES, scopes, breaking_emoji


def process_commit_message(
    commit_message: str,
    commit_types: dict[str, str],
    scopes: dict[str, str],
    breaking_emoji: str,
) -> str:
    lines = commit_message.split("\n")
    title = lines[0]
    body = "\n".join(lines[1:])

    match = re.match(BASE_PATTERN, title)
    if match:
        # get match groups
        commit_type = match.group("type")
        scope = match.group("scope")
        breaking = match.group("breaking")

        # set emojis
        first_emoji = commit_types.get(commit_type)
        if first_emoji is None:
            msg = f"Commit type '{commit_type}' does not have a corresponding emoji."
            raise NoConventionalCommitTypeFoundError(msg)
        second_emoji = scopes.get(scope, "") if scope else ""
        emojis = f"{breaking_emoji if breaking else ''}{first_emoji}{second_emoji}"

        # put together message
        commit_type_end = match.end()
        updated_title = f"{title[:commit_type_end].strip()} {emojis} {title[commit_type_end:].strip()}"
        return f"{updated_title}\n{body}"

    raise NonConventionalCommitError


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process commit messages and add emojis.",
    )
    parser.add_argument(
        "commit_message_file",
        type=Path,
        help="Path to the commit message file",
    )
    args = parser.parse_args()

    commit_types, scopes, breaking_emoji = load_custom_rules()

    with args.commit_message_file.open("r") as file:
        commit_message = file.read().strip()

    try:
        processed_message = process_commit_message(
            commit_message,
            commit_types,
            scopes,
            breaking_emoji,
        )
        with args.commit_message_file.open("w") as file:
            file.write(processed_message)
        print(
            "🎉 Commit message follows Conventional Commits rules and has been updated with an emoji.",
        )
        sys.exit(0)
    except (NonConventionalCommitError, NoConventionalCommitTypeFoundError) as e:
        print(f"💥 Commit message: '{commit_message}'\n💥 {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

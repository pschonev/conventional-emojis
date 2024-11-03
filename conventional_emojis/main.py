#!/usr/bin/env python3
import argparse
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@dataclass
class NonConventionalCommitError(Exception):
    """Raised when a commit message doesn't follow the Conventional Commits format."""

    message: str = "Commit message does not follow Conventional Commits rules."

    def __str__(self) -> str:
        return self.message


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

BASE_PATTERN: str = r"^(?P<type>\w+)(\((?P<scope>.+)\))?(!)?:"


def load_custom_rules(
    config_file: Path = Path("conventional_emojis_config.yaml"),
) -> dict[str, str]:
    if not config_file.exists():
        return COMMIT_TYPES

    with config_file.open("r") as file:
        config_data = yaml.safe_load(file)

    COMMIT_TYPES.update(dict(config_data.get("types", {}).items()))

    return COMMIT_TYPES


def process_commit_message(
    commit_message: str,
    commit_types: dict[str, str],
) -> str:
    match = re.match(BASE_PATTERN, commit_message)
    if match:
        commit_type = match.group("type")
        emoji = commit_types.get(commit_type)
        if emoji:
            commit_type_end = match.end()
            return f"{commit_message[:commit_type_end].strip()} {emoji} {commit_message[commit_type_end:].strip()}"

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
    parser.add_argument(
        "--emoji-disabled",
        action="store_true",
        help="Disable emojis in commit messages",
    )
    args = parser.parse_args()

    commit_types = load_custom_rules()

    with args.commit_message_file.open("r") as file:
        commit_message = file.read().strip()

    try:
        processed_message = process_commit_message(commit_message, commit_types)
        if not args.emoji_disabled:
            with args.commit_message_file.open("w") as file:
                file.write(processed_message)
        logger.info(
            "🎉 Commit message follows Conventional Commits rules and has been updated with an emoji.",
        )
        sys.exit(0)
    except NonConventionalCommitError as e:
        logger.warning("Commit message: '%s'\n💥 %s", commit_message, e)
        sys.exit(1)


if __name__ == "__main__":
    main()

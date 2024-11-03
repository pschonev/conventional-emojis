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
class ConfigLoader:
    config_file: Path

    def load_yaml_config(self) -> dict:
        if not self.config_file.exists():
            print("No custom rules YAML file found.")
            return {}
        with self.config_file.open("r") as file:
            return yaml.safe_load(file)

    def parse_config(
        self,
        config_data: dict,
        *,
        allow_types_as_scopes: bool,
    ) -> tuple[dict[str, str], dict[str, str], str]:
        commit_types = COMMIT_TYPES.copy()
        commit_types.update(config_data.get("types", {}))

        scopes = config_data.get("scopes", {})
        if allow_types_as_scopes:
            scopes.update(commit_types)

        breaking_emoji = config_data.get("breaking", BREAKING)

        return commit_types, scopes, breaking_emoji


@dataclass
class CommitMessageProcessor:
    commit_types: dict[str, str]
    scopes: dict[str, str]
    breaking_emoji: str

    def extract_commit_details(
        self,
        commit_message: str,
    ) -> tuple[str, str, str, str, str]:
        lines = commit_message.split("\n")
        title = lines[0]
        body = "\n".join(lines[1:])
        match = re.match(BASE_PATTERN, title)
        if not match:
            raise NonConventionalCommitError
        commit_type = match.group("type")
        scope = match.group("scope")
        breaking = match.group("breaking")
        return title, body, commit_type, scope, breaking

    def set_emojis(self, commit_type: str, scope: str, breaking: str) -> str:
        first_emoji = self.commit_types.get(commit_type)
        if first_emoji is None:
            msg = f"Commit type '{commit_type}' does not have a corresponding emoji."
            raise NoConventionalCommitTypeFoundError(msg)
        second_emoji = self.scopes.get(scope, "") if scope else ""
        return f"{self.breaking_emoji if breaking else ''}{first_emoji}{second_emoji}"

    def update_commit_message(self, title: str, body: str, emojis: str) -> str:
        match = re.match(BASE_PATTERN, title)
        if not match:
            raise NonConventionalCommitError
        commit_type_end = match.end()
        updated_title = f"{title[:commit_type_end].strip()} {emojis} {title[commit_type_end:].strip()}"
        return f"{updated_title}\n{body}"

    def process_commit_message(self, commit_message: str) -> str:
        title, body, commit_type, scope, breaking = self.extract_commit_details(
            commit_message,
        )
        emojis = self.set_emojis(commit_type, scope, breaking)
        return self.update_commit_message(title, body, emojis)


def process_conventional_commit(
    *,
    commit_message_file: Path,
    allow_types_as_scopes: bool,
    config_file: Path = Path("conventional_emojis_config.yaml"),
) -> None:
    config_loader = ConfigLoader(config_file)
    config_data = config_loader.load_yaml_config()
    commit_types, scopes, breaking_emoji = config_loader.parse_config(
        config_data,
        allow_types_as_scopes=allow_types_as_scopes,
    )

    processor = CommitMessageProcessor(commit_types, scopes, breaking_emoji)

    with commit_message_file.open("r") as file:
        commit_message = file.read().strip()

    try:
        processed_message = processor.process_commit_message(commit_message)
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
        "--disable-types-as-scopes",
        action="store_true",
        help="Disable using types as scopes in commit messages",
    )
    args = parser.parse_args()

    process_conventional_commit(
        commit_message_file=args.commit_message_file,
        allow_types_as_scopes=not args.disable_types_as_scopes,
    )


if __name__ == "__main__":
    main()

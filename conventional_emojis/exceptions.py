from dataclasses import dataclass


@dataclass
class NonConventionalCommitError(Exception):
    """Raised when a commit message doesn't follow the Conventional Commits format."""

    message: str = "Commit message does not follow Conventional Commits rules."

    def __str__(self) -> str:
        return self.message


@dataclass
class NoConventionalCommitTypeFoundError(Exception):
    """Raised when type in the commit message is not found in the commit types."""

    message: str = "Commit type not found in the commit types."

    def __str__(self) -> str:
        return self.message

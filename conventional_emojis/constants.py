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
BASE_PATTERN: str = r"^(?P<type>\w+)(\((?P<scope>.+)\))?(?P<breaking>!)?:"

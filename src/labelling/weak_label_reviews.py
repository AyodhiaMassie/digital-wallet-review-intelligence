from pathlib import Path

import yaml


RULES_FILE_PATH = Path(__file__).resolve().parents[2] / "config" / "weak_label_rules.yaml"


def load_weak_label_rules() -> dict:
    """Load the weak label rules YAML file."""

    if not RULES_FILE_PATH.exists():
        raise FileNotFoundError(
            f"Weak label rules file not found: {RULES_FILE_PATH}"
        )

    with RULES_FILE_PATH.open("r", encoding="utf-8") as rules_file:
        rules = yaml.safe_load(rules_file)

    if not isinstance(rules, dict):
        raise ValueError("Weak label rules file must contain a YAML dictionary.")

    return rules


def get_issue_priority_labels(rules: dict) -> list:
    """Read the issue priority labels from the rules file."""

    if "main_issue_priority" in rules:
        return rules["main_issue_priority"]

    return rules.get("issue_rule_priority", [])


def print_rules_summary(rules: dict) -> None:
    """Print a small summary of the weak label rules."""

    rules_version = rules.get("rules_version", "not found")
    scope_rules = rules.get("scope_rules", {})
    issue_rules = rules.get("issue_rules", {})
    issue_priority_labels = get_issue_priority_labels(rules)

    print("Weak label rules summary")
    print(f"Rules version: {rules_version}")
    print(f"Number of scope rules: {len(scope_rules)}")
    print(f"Number of issue rules: {len(issue_rules)}")
    print(f"Number of issue priority labels: {len(issue_priority_labels)}")


def main() -> None:
    """Load weak label rules and print a summary."""

    rules = load_weak_label_rules()
    print_rules_summary(rules)


if __name__ == "__main__":
    main()

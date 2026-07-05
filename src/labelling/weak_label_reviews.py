from pathlib import Path

import yaml

# file path to weak_label_rules.yaml
RULES_FILE_PATH = Path(__file__).resolve().parents[2] / "config" / "weak_label_rules.yaml"

def load_weak_label_rules() -> dict:
    """Load the weak label rules YAML file."""

    # handle case that file does not exist
    if not RULES_FILE_PATH.exists():
        raise FileNotFoundError(
            f"Weak label rules file not found: {RULES_FILE_PATH}"
        )

    # if file exists, open it and convert to python dictionary
    # opened file is referenced with var "rules"
    with RULES_FILE_PATH.open("r", encoding="utf-8") as rules_file:
        rules = yaml.safe_load(rules_file)

    if not isinstance(rules, dict):
        raise ValueError("Weak label rules file must contain a YAML dictionary.")

    # return the rules
    return rules


def get_issue_priority_labels(rules: dict) -> list:
    """Read the issue priority labels from the rules file."""

    # get the issue_rule_priority section of the file
    return rules.get("issue_rule_priority", [])

def get_empty_rule_match() -> dict:
    """Return the same match structure when no rule terms matched."""

    return {
        "matched": False,
        "matched_phrases": [],
        "matched_keywords": [],
        "matched_terms": [],
    }


def match_rule_section(review_text: str, rule_section: dict) -> dict:
    """Check whether review text matches phrases or keywords in one rule section."""

    # convert review text to lowercase
    review_text_lower = review_text.lower()
    
    # create list to store matched phrases
    matched_phrases = []

    # create list to store matched keywords
    matched_keywords = []

    # create set to store seen terms (keywords and phrases)
    seen_terms = set()

    # Check for each phrase defined in the rules
    for phrase in rule_section.get("phrases", []):
        
        # convert the phrase to lowercase
        phrase_lower = phrase.lower()
        
        # if the phrase is found in the review text and not seen yet
        if phrase_lower in review_text_lower and phrase_lower not in seen_terms:
            
            # add the phrase to matched_phrases list
            matched_phrases.append(phrase)

            # add the phrase to seen_terms list
            seen_terms.add(phrase_lower)

    # Now we check for keywords
    # Check for each keyword defined in rules
    for keyword in rule_section.get("keywords", []):
        
        # convert the keyword to lowercase
        keyword_lower = keyword.lower()

        # if the keyword is found in the review text and is not seen yet
        if keyword_lower in review_text_lower and keyword_lower not in seen_terms:
            
            # add the keyword to the matched_keywords_list
            matched_keywords.append(keyword)
            
            # add the keyword to the seen_terms set
            seen_terms.add(keyword_lower)

    # return python dict that contains summarized info about
    # how the review text is labeled
    return {
        # True or False depending on if a matched phrase or keyword was found in the review text
        "matched": bool(matched_phrases or matched_keywords),
        # list of matched phrases
        "matched_phrases": matched_phrases,
        # list of matched keywords
        "matched_keywords": matched_keywords,
        # list of matched terms (phrases and keywords combined)
        "matched_terms": matched_phrases + matched_keywords,
    }


def classify_review_scope(review_text: str, rules: dict) -> dict:
    """Classify whether a review is wallet-related or non-wallet-related."""

    # get the rules that define whether a review is wallet related or not
    scope_rules = rules.get("scope_rules", {})
    
    # find keywords/phrases that could classify the review as wallet related
    wallet_match = match_rule_section(
        review_text, scope_rules.get("wallet_related", {})
    )

    # find keywords/phrases that could classify the review as non wallet related
    non_wallet_match = match_rule_section(
        review_text, scope_rules.get("non_wallet_related", {})
    )

    # check first if there is a match in the review and wallet related
    # keywords and phrases
    if wallet_match["matched"]:
        return {
            "scope_label": "wallet_related",
            "matched_scope_terms": wallet_match["matched_terms"],
            "scope_match": wallet_match,
        }

    # then check if there is a match in the review and non wallet related
    # keywords and phrases
    if non_wallet_match["matched"]:
        return {
            "scope_label": "non_wallet_related",
            "matched_scope_terms": non_wallet_match["matched_terms"],
            "scope_match": non_wallet_match,
        }

    # If we are unable to classify the review as wallet or non wallet related
    # based on the rules we have defined, set the review to be wallet related
    # by default
    return {
        "scope_label": "wallet_related",
        "matched_scope_terms": [],
        "scope_match": get_empty_rule_match(),
    }


def calculate_rule_match_score(rule_match: dict) -> int:
    """Calculate how strong a phrase or keyword rule match was."""

    phrase_count = len(rule_match["matched_phrases"])
    keyword_count = len(rule_match["matched_keywords"])

    # if we found more than one matching phrase 
    # OR more than or equal to 1 matching phrase AND matching keyword
    # set rule match score to the maximum score of 5
    if phrase_count > 1 or (phrase_count >= 1 and keyword_count >= 1):
        return 5

    # if we find just 1 matching phrase, set rule match score to 4
    if phrase_count == 1:
        return 4

    # if we find more than 1 matching keyword, set rule match score to 3
    if keyword_count > 1:
        return 3

    # if we find just 1 matching keyword, set rule match score to 2
    if keyword_count == 1:
        return 2

    # otherwise, return default rule match score of 1
    return 1


def classify_main_issue(review_text: str, scope_label: str, rules: dict) -> dict:
    """Classify the main issue for a review."""

    # if the review is non wallet related
    # classify the review as "other_unclear"
    if scope_label == "non_wallet_related":
        return {
            "issue_label": "other_unclear",
            "matched_issue_terms": [],
            "issue_match": get_empty_rule_match(),
        }

    # get the rules for issue classification
    issue_rules = rules.get("issue_rules", {})
    
    # get the issue priority labels
    issue_priority_labels = get_issue_priority_labels(rules)

    # Use the configured priority order and stop at the first matching issue
    # Loop through each issue in the configured order
    for issue_label in issue_priority_labels:
        
        # Look for a match in keywords/phrases that can classify the review to the current issue
        issue_match = match_rule_section(review_text, issue_rules.get(issue_label, {}))
        
        # if we found a matching keyword/phrase, classify the review to that issue
        if issue_match["matched"]:
            return {
                "issue_label": issue_label,
                "matched_issue_terms": issue_match["matched_terms"],
                "issue_match": issue_match,
            }

    # if we cant find a match for the review with any of the issues
    # classify it as "other_unclear"
    return {
        "issue_label": "other_unclear",
        "matched_issue_terms": [],
        "issue_match": get_empty_rule_match(),
    }


def classify_review(review_text: str, rules: dict) -> dict:
    """Classify one review using the weak label rules."""

    # classify the review as either wallet or non-wallet related
    scope_result = classify_review_scope(review_text, rules)
    
    # classify the review under an issue category
    issue_result = classify_main_issue(
        review_text, scope_result["scope_label"], rules
    )

    # if the review is non-wallet related calculate the confidence score 
    # for how likely the issue is non wallet related
    if scope_result["scope_label"] == "non_wallet_related":
        rule_match_score = calculate_rule_match_score(scope_result["scope_match"])
    
    # otherwise, if the review is wallet-related, calculate the confidence score
    # for how likely the review is about the classified issue
    else:
        rule_match_score = calculate_rule_match_score(issue_result["issue_match"])

    # return summary dict
    return {
        "scope_label": scope_result["scope_label"],
        "issue_label": issue_result["issue_label"],
        "matched_scope_terms": scope_result["matched_scope_terms"],
        "matched_issue_terms": issue_result["matched_issue_terms"],
        "rule_match_score": rule_match_score,
    }

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
    """Load weak label rules, print a summary, and classify example reviews."""

    rules = load_weak_label_rules()
    print_rules_summary(rules)

    test_reviews = [
        "I can't access my wallet. The app keeps saying login failed.",
        "My wallet balance is missing after the latest update.",
        "The app crashes every time I try to open it.",
        "I love the new design, very clean and easy to use.",
        "My transaction is stuck and the payment is still pending.",
        "The customer support team is not replying to my messages.",
        "I forgot my wallet password and cannot recover my account.",
        "The app is slow and freezes on the home screen.",
    ]

    print()
    print("Test review classifications")
    for review in test_reviews:
        result = classify_review(review, rules)

        print("=" * 80)
        print("Review:", review)
        print("Scope label:", result["scope_label"])
        print("Issue label:", result["issue_label"])
        print("Matched scope terms:", result["matched_scope_terms"])
        print("Matched issue terms:", result["matched_issue_terms"])
        print("Rule match score:", result["rule_match_score"])


if __name__ == "__main__":
    main()

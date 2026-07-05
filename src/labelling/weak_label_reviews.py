from collections import Counter
import json
from pathlib import Path

from sqlalchemy import text
import yaml

from src.database.connection import get_database_engine

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


def fetch_clean_reviews(connection) -> list[dict]:
    """Read cleaned reviews from the clean_reviews table."""

    # create sql query
    # reads the fields needed for weak labelling from clean_reviews
    sql = text(
        """
        SELECT
            review_id,
            app_id,
            cleaned_review_text
        FROM clean_reviews
        ORDER BY review_id;
        """
    )

    # send the sql query to postgresql
    result = connection.execute(sql)

    # return a list of dictionaries so each review is easy to read in Python
    return [dict(row) for row in result.mappings()]


def classify_clean_reviews(clean_reviews: list[dict], rules: dict) -> list[dict]:
    """Classify clean reviews in memory without updating the database."""

    classified_reviews = []
    label_version = rules.get("rules_version", "v1")

    # loop through each clean review and classify the cleaned text
    for clean_review in clean_reviews:
        classification = classify_review(clean_review["cleaned_review_text"], rules)

        classified_reviews.append(
            {
                "review_id": clean_review["review_id"],
                "app_id": clean_review["app_id"],
                "cleaned_review_text": clean_review["cleaned_review_text"],
                "scope_label": classification["scope_label"],
                "issue_label": classification["issue_label"],
                "matched_scope_terms": classification["matched_scope_terms"],
                "matched_issue_terms": classification["matched_issue_terms"],
                "rule_match_score": classification["rule_match_score"],
                "label_version": label_version,
            }
        )

    return classified_reviews


def prepare_weak_label_for_database(classified_review: dict) -> dict:
    """Prepare one classified review for inserting into review_labels_weak."""

    return {
        "review_id": classified_review["review_id"],
        "app_id": classified_review["app_id"],
        "scope_label": classified_review["scope_label"],
        "issue_label": classified_review["issue_label"],
        "matched_scope_terms": json.dumps(classified_review["matched_scope_terms"]),
        "matched_issue_terms": json.dumps(classified_review["matched_issue_terms"]),
        "rule_match_score": classified_review["rule_match_score"],
        "label_version": classified_review["label_version"],
    }


def upsert_weak_labels(connection, classified_reviews: list[dict]) -> int:
    """Insert weak labels, or update them if they already exist."""

    # if there are no classified reviews to write, stop and return 0
    if not classified_reviews:
        return 0

    # create sql query
    # inserts weak labels into review_labels_weak table
    sql = text(
        """
        INSERT INTO review_labels_weak (
            review_id,
            app_id,
            scope_label,
            issue_label,
            matched_scope_terms,
            matched_issue_terms,
            rule_match_score,
            label_version
        )
        VALUES (
            :review_id,
            :app_id,
            :scope_label,
            :issue_label,
            CAST(:matched_scope_terms AS JSONB),
            CAST(:matched_issue_terms AS JSONB),
            :rule_match_score,
            :label_version
        )
        ON CONFLICT (review_id) DO UPDATE
        SET
            app_id = EXCLUDED.app_id,
            scope_label = EXCLUDED.scope_label,
            issue_label = EXCLUDED.issue_label,
            matched_scope_terms = EXCLUDED.matched_scope_terms,
            matched_issue_terms = EXCLUDED.matched_issue_terms,
            rule_match_score = EXCLUDED.rule_match_score,
            label_version = EXCLUDED.label_version,
            labelled_at = CURRENT_TIMESTAMP;
        """
    )

    # set a counter to track each weak label that gets inserted or updated
    inserted_or_updated_count = 0

    # loop through each classified review and upsert the weak label
    for classified_review in classified_reviews:
        weak_label = prepare_weak_label_for_database(classified_review)
        result = connection.execute(sql, weak_label)
        inserted_or_updated_count += result.rowcount

    # return the count of rows inserted or updated
    return inserted_or_updated_count

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


def print_label_counts(title: str, label_counts: Counter) -> None:
    """Print counts for each label."""

    print()
    print(title)

    for label, count in label_counts.items():
        print(f"{label}: {count}")


def print_classification_samples(classified_reviews: list[dict], sample_limit: int = 10) -> None:
    """Print a small sample of classified clean reviews."""

    print()
    print(f"Sample classification results, up to {sample_limit}")

    for classified_review in classified_reviews[:sample_limit]:
        print("=" * 80)
        print("Review ID:", classified_review["review_id"])
        print("App ID:", classified_review["app_id"])
        print("Cleaned review text:", classified_review["cleaned_review_text"])
        print("Scope label:", classified_review["scope_label"])
        print("Issue label:", classified_review["issue_label"])
        print("Matched scope terms:", classified_review["matched_scope_terms"])
        print("Matched issue terms:", classified_review["matched_issue_terms"])
        print("Rule match score:", classified_review["rule_match_score"])


def main() -> None:
    """Load weak label rules, classify clean_reviews rows, and save weak labels."""

    rules = load_weak_label_rules()
    print_rules_summary(rules)

    # connect to database
    engine = get_database_engine()

    with engine.begin() as connection:
        clean_reviews = fetch_clean_reviews(connection)

        # if there are no clean reviews, stop without crashing
        if not clean_reviews:
            print()
            print("Weak label classification summary")
            print("Clean reviews read: 0")
            print("No clean reviews found in clean_reviews. Nothing to classify.")
            return

        # classify rows in memory
        classified_reviews = classify_clean_reviews(clean_reviews, rules)

        # insert or update one weak label row for each clean review
        inserted_or_updated_count = upsert_weak_labels(
            connection,
            classified_reviews,
        )

    scope_label_counts = Counter(
        classified_review["scope_label"]
        for classified_review in classified_reviews
    )
    issue_label_counts = Counter(
        classified_review["issue_label"]
        for classified_review in classified_reviews
    )

    print()
    print("Weak label classification summary")
    print(f"Clean reviews read: {len(clean_reviews)}")

    print_label_counts("Counts by scope_label", scope_label_counts)
    print_label_counts("Counts by issue_label", issue_label_counts)
    print_classification_samples(classified_reviews)

    print()
    print("Weak label database write summary")
    print(f"Weak labels inserted or updated: {inserted_or_updated_count}")


if __name__ == "__main__":
    main()

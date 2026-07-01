import re


def clean_review_text(review_text: str | None) -> str:
    """Clean review text using simple formatting rules."""
    
    # convert empty review text to empty string
    if review_text is None:
        return ""

    # convert review text to string
    text = str(review_text)
    # remove whitespaces at the start and end of the text
    text = text.strip()
    # check for one or more whitespace characters and replace with single space
    text = re.sub(r"\s+", " ", text)
    # set text to lowercase
    text = text.lower()

    return text

def count_words(text: str) -> int:
    """Count number of words in cleaned review text"""
    cleaned_text = clean_review_text(text)

    if cleaned_text == "":
        return 0

    return len(cleaned_text.split())

def is_empty_text(text: str) -> bool:
    """Check whether text is empty after trimming whitespace."""
    return str(text).strip() == ""

import pandas as pd

def deduplicate_reviews(review_df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    duplicate_mask = review_df.duplicated(subset=["review_id"], keep="first")
    duplicates_skipped = int(duplicate_mask.sum())

    deduplicated_df = review_df.loc[~duplicate_mask].copy()

    return deduplicated_df, duplicates_skipped
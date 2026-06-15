from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class ReviewSource(ABC):
    """
    Class blueprint for review data sources.

    Any review source should provide a fetch_reviews method that returns
    review reecords from apps in that review source as a pandas DataFrame.
    """

    @abstractmethod
    def fetch_reviews(
        self,
        app_config: dict[str, Any],
        review_count: int,
    ) -> pd.DataFrame:
        """
        Fetch reviews for one app and return review records.
        """
        pass
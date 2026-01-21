"""
External Database Integration.

TODO: Rename this folder to match your external database name
(e.g., clinicaltrials, pubmed, etc.)
"""

from .client import ExternalDBClient
from .agent import SearchAgent
from .transformer import DataTransformer

__all__ = ["ExternalDBClient", "SearchAgent", "DataTransformer"]

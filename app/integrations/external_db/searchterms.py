"""
Search terms and keywords for external database queries.

This module contains predefined search terms, keywords, and phrases
that are useful for searching the external database.
"""

from enum import Enum


class SearchCategory(str, Enum):
    """Categories for organizing search terms."""
    
    GENERAL = "osteosarcoma"
    # TODO: Add your specific categories
    # Example categories:
    # CONDITION = "condition"
    # TREATMENT = "treatment"
    # STUDY_TYPE = "study_type"
    # PHASE = "phase"


# Main search terms organized by category
SEARCH_TERMS: dict[SearchCategory, list[str]] = {
    SearchCategory.GENERAL: [
        # TODO: Add your search terms here
        # Example terms:
        # "cancer",
        # "diabetes",
        # "clinical trial",
        # "randomized controlled trial",
    ],
    
    # TODO: Add more categories with their terms
    # SearchCategory.CONDITION: [
    #     "alzheimer",
    #     "parkinson",
    #     "multiple sclerosis",
    # ],
}

# Synonyms and related terms for query expansion
SYNONYMS: dict[str, list[str]] = {
    # TODO: Add synonyms for better search coverage
    # Example:
    # "cancer": ["tumor", "neoplasm", "malignancy", "carcinoma"],
    # "heart attack": ["myocardial infarction", "MI", "cardiac arrest"],
}

# Common filters or modifiers
SEARCH_MODIFIERS: list[str] = [
    # TODO: Add common modifiers
    # Example:
    # "latest",
    # "ongoing",
    # "completed",
    # "peer reviewed",
]

# Excluded terms (terms to filter out from results)
EXCLUDED_TERMS: list[str] = [
    # TODO: Add terms you want to exclude from searches
]


def get_terms_by_category(category: SearchCategory) -> list[str]:
    """
    Get all search terms for a specific category.
    
    Args:
        category: The category to retrieve terms for
        
    Returns:
        List of search terms
    """
    return SEARCH_TERMS.get(category, [])


def get_all_terms() -> list[str]:
    """
    Get all search terms from all categories.
    
    Returns:
        Flat list of all search terms
    """
    all_terms = []
    for terms in SEARCH_TERMS.values():
        all_terms.extend(terms)
    return all_terms


def expand_query(term: str) -> list[str]:
    """
    Expand a search term with its synonyms.
    
    Args:
        term: The original search term
        
    Returns:
        List containing the original term and its synonyms
    """
    expanded = [term]
    if term.lower() in SYNONYMS:
        expanded.extend(SYNONYMS[term.lower()])
    return expanded


def build_search_query(
    terms: list[str],
    modifiers: list[str] | None = None,
    expand_synonyms: bool = False
) -> str:
    """
    Build a search query string from terms and modifiers.
    
    Args:
        terms: List of search terms
        modifiers: Optional list of modifiers to add
        expand_synonyms: Whether to include synonyms
        
    Returns:
        Formatted search query string
    """
    query_terms = []
    
    for term in terms:
        if expand_synonyms:
            query_terms.extend(expand_query(term))
        else:
            query_terms.append(term)
    
    if modifiers:
        query_terms.extend(modifiers)
    
    # TODO: Customize query format based on your external database's syntax
    # This is a simple space-separated format
    return " ".join(query_terms)

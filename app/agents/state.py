from typing import List, Dict
from typing_extensions import TypedDict


class OutfitAgentState(TypedDict):
    """State schema for the outfit recommendation workflow"""
    user_profile: Dict
    wardrobe_items: List[Dict]
    request: Dict
    filtered_items: Dict[str, List[Dict]]
    outfit_suggestions: List[Dict]
    reasoning: str

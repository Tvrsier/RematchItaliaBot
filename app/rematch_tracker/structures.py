from typing import TypedDict


class ResolveResponse(TypedDict):
    """
    Represents the response structure for a resolve operation.
    """
    platform: str
    platform_id: str
    display_name: str
    success: bool


class ResolveError(TypedDict):
    error: str


class ProfilePlayer(TypedDict):
    platform: str
    platform_id: str
    display_name: str
    avatar_asset: str
    banner_asset: str
    background_asset: str
    title: str
    level: int
    last_updated_at: str  # ISO8601

class ProfileRank(TypedDict):
    current_league: int
    current_division: int

class ProfileResponse(TypedDict):
    player: ProfilePlayer
    rank: ProfileRank
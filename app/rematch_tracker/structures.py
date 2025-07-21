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
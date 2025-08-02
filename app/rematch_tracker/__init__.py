from typing import Optional

from app.logger import logger
import aiohttp
import os

from app.lib.db.schemes import PlatformEnum
from app.rematch_tracker.structures import ResolveResponse
from rematch_tracker.structures import ProfileResponse, ProfilePlayer, ProfileRank

RESOLVE_URL = os.getenv("RESOLVE_URL", None)
PROFILE_URL = os.getenv("PROFILE_URL", None)

if not RESOLVE_URL or not PROFILE_URL:
    logger.error("RESOLVE_URL or PROFILE_RUL not found in environment variables. Please set it in your .env file.")
    raise RuntimeError("RESOLVE_URL or PROFILE_URL not found in environment variables. Please set it in your .env file.")


async def resolve_rematch_id(
        platform: PlatformEnum,
        identifier: str,
        timeout: float = 10.0
) -> Optional[ProfileResponse]:
    """
    Resolve a Rematch ID to a platform and identifier.
    :param platform:
        The platform to resolve the Rematch ID for.
    :param identifier:
        The identifier to resolve.
    :param timeout:
        The timeout for the request in seconds.
    :return:
        A dictionary containing the resolved player in rematch_tracker
        or None if the resolution fails.
    """
    payload = {"platform": platform.value, "identifier": identifier}
    headers = {"Content-Type": "application/json"}

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        try:
            async with session.post(RESOLVE_URL, json=payload, headers=headers) as response:
                text = await response.text()
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") is True:
                        returned = data.get("platform")
                        expected_platform = platform.value if platform != PlatformEnum.PSN else "psn"
                        if returned != expected_platform:
                            logger.warning(
                                "Resolved platform %s does not match requested platform %s",
                                returned, platform.value
                            )
                            return None

                        resolve = ResolveResponse(
                            platform=data.get("platform"),
                            platform_id=data.get("platform_id"),
                            display_name=data.get("display_name"),
                            success=True
                        )
                        return await get_rematch_profile(resolve=resolve)
                    else:
                        logger.error("Resolve: success flag false for %s: %s", platform, identifier)
                        return None
                else:
                    err = await response.json()
                    logger.error(f"Resolve: failed {platform}/{identifier} -> {response.status}: "
                                f"{err.get("error", "Unknown error")}")
                    return None

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error in resolve_rematch_id: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.exception(f"Unexpected error in resolve_rematch_id: {e}", exc_info=True)
            return None


async def get_rematch_profile(
        timeout: float = 10.0,
        resolve: ResolveResponse | None = None,
        platform: Optional[str] = None,
        platform_id: Optional[str] = None
) -> Optional[ProfileResponse]:
    """
        Get rematch profile from the tracker given the tracker resolve response
        :param platform: The platform to use for the request.
        :param platform_id: The platform ID to use for the request.
        :param resolve:
            The resolve response from the previous call to scrap/resolve
        :param timeout:
            The timeout for the request in seconds.
        :return:
            A dictionary containing the fetched player
            or None if the resolution fails.
        """
    payload = {
        "platform": resolve["platform"] if platform is None else platform,
        "platformId": resolve["platform_id"] if platform_id is None else platform_id,
    }
    headers = {"Content-Type": "application/json"}

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        try:
            async with session.post(PROFILE_URL, json=payload, headers=headers) as resp:
                text = await resp.text()
                if resp.status == 200:
                    data = await resp.json()
                    if "player" in data and "rank" in data:
                        profile_player = ProfilePlayer(**data["player"])
                        rank = ProfileRank(**data["rank"])
                        return ProfileResponse(player= profile_player, rank=rank)
                    else:
                        logger.error(f"Profile: no response for player id {resolve["platform_id"]}\n"
                                     f"response: {data}")
                        return None

                elif resp.status == 400:
                    err = await resp.json()
                    logger.warning(
                        f"Profile bad request {resolve['platform']}/{resolve["platform_id"]} -> {err.get("error")}"
                    )
                    return None
                else:
                    err = await resp.json()
                    logger.warning(
                        f"profile server error {resolve["platform"]}/{resolve["platform_id"]} -> "
                        f"{err.get("error")} ({resp.status})"
                    )
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error in get_rematch_profile: {e}", exception=e, exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_rematch_profile: {e}", exception=e, exc_info=True)
            return None

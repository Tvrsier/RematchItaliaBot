from typing import Optional

from app.logger import logger
import aiohttp
import os

from app.lib.db.schemes import PlatformEnum
from app.rematch_tracker.structures import ResolveResponse

RESOLVE_URL = os.getenv("RESOLVE_URL", None)

if not RESOLVE_URL:
    logger.error("RESOLVE_URL not found in environment variables. Please set it in your .env file.")
    raise RuntimeError("RESOLVE_URL not found in environment variables. Please set it in your .env file.")


async def resolve_rematch_id(
        platform: PlatformEnum,
        identifier: str,
        timeout: float = 10.0
) -> Optional[ResolveResponse]:
    """
    Resolve a Rematch ID to a platform and identifier.
    :param platform:
        The platform to resolve the Rematch ID for.
    :param identifier:
        The identifier to resolve.
    :param timeout:
        The timeout for the request in seconds.
    :return:
        A dictionary containing the resolved platform, platform ID, and display name if successful,
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
                        # TODO call the profile API to get the rematch profile, check for steam players
                        return ResolveResponse(
                            platform=data.get("platform"),
                            platform_id=data.get("platform_id"),
                            display_name=data.get("display_name"),
                            success=True
                        )
                    else:
                        logger.info("Resolve: success flag false for %s: %s", platform, identifier)
                        return None
                else:
                    err = await response.json()
                    logger.info(f"Resolve: failed {platform}/{identifier} -> {response.status}: "
                                f"{err.get("error", "Unknown error")}")
                    return None

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error in resolve_rematch_id: {e}", exc_info=True, exception=e)
            return None
        except Exception as e:
            logger.exception(f"Unexpected error in resolve_rematch_id: {e}", exc_info=True, exception=e)
            return None
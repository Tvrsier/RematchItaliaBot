import dotenv
dotenv.load_dotenv("../.env")

from rematch_tracker import ProfileResponse, ProfilePlayer, ProfileRank
import unittest
from app.rematch_tracker import resolve_rematch_id
from app.lib.db.schemes import PlatformEnum



class TestRematchTracker(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        pass

    async def asyncTearDown(self):
        pass



    async def test_resolve_profile_rematch_id(self):
        expected_platform_id = "3502400170348263876"
        expected_display_name = "Tvrsier"

        response: ProfileResponse | None = await resolve_rematch_id(
            platform=PlatformEnum.PSN,
            identifier=expected_display_name
        )
        player: ProfilePlayer = response["player"]
        rank: ProfileRank = response["rank"]
        self.assertIsNotNone(response)
        self.assertEqual(player["platform_id"], expected_platform_id)
        self.assertEqual(player["display_name"], expected_display_name)
        self.assertEqual(rank["current_league"], 5)




    async def test_resolve_rematch_id_invalid_platform(self):
        response = await resolve_rematch_id(
            platform=PlatformEnum.STEAM,
            identifier="invalid_identifier"
        )

        self.assertIsNone(response, "Response should be None for invalid platform or identifier")
import dotenv
dotenv.load_dotenv("../.env")
import unittest
from app.rematch_tracker import resolve_rematch_id
from app.lib.db.schemes import PlatformEnum



class TestRematchTracker(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        pass

    async def asyncTearDown(self):
        pass


    async def test_resolve_rematch_id(self):
        expected_platform_id = "3502400170348263876"
        expected_display_name = "Tvrsier"

        response = await resolve_rematch_id(
            platform=PlatformEnum.PSN,
            identifier=expected_platform_id
        )

        self.assertIsNotNone(response, "Response should not be None")
        self.assertEqual(response.get("platform_id"), expected_platform_id, "Platform ID does not match")
        self.assertEqual(response.get("display_name"), expected_display_name, "Display name does not match")
        self.assertTrue(response.get("success"), "Success flag should be True")
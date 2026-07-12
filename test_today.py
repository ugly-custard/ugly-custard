import importlib
import os
import unittest
from unittest.mock import patch


class FakeResponse:
    def __init__(self, status_code, payload, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


class RecursiveLocTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("ACCESS_TOKEN", "test-token")
        os.environ.setdefault("USER_NAME", "test-user")
        import today

        cls.today = importlib.reload(today)
        cls.today.OWNER_ID = {"id": "owner-id"}

    def _history_payload(self, has_next_page, end_cursor):
        return {
            "data": {
                "repository": {
                    "defaultBranchRef": {
                        "target": {
                            "history": {
                                "edges": [
                                    {
                                        "node": {
                                            "author": {"user": {"id": "owner-id"}},
                                            "additions": 2,
                                            "deletions": 1,
                                        }
                                    }
                                ],
                                "pageInfo": {
                                    "endCursor": end_cursor,
                                    "hasNextPage": has_next_page,
                                },
                            }
                        }
                    }
                }
            }
        }

    def test_recursive_loc_handles_many_pages_without_recursion_error(self):
        total_pages = 1205

        def fake_post(_url, json, headers):  # noqa: ARG001
            cursor = json["variables"]["cursor"]
            index = 0 if cursor is None else int(cursor)
            has_next_page = index < total_pages - 1
            end_cursor = str(index + 1) if has_next_page else None
            return FakeResponse(200, self._history_payload(has_next_page, end_cursor))

        with patch.object(self.today.requests, "post", side_effect=fake_post):
            result = self.today.recursive_loc("owner", "repo", [], [])

        self.assertEqual(result, (total_pages * 2, total_pages, total_pages))

    def test_recursive_loc_stops_if_cursor_does_not_advance(self):
        def fake_post(_url, json, headers):  # noqa: ARG001
            cursor = json["variables"]["cursor"]
            return FakeResponse(
                200, self._history_payload(has_next_page=True, end_cursor=cursor)
            )

        with patch.object(self.today.requests, "post", side_effect=fake_post) as mocked:
            result = self.today.recursive_loc("owner", "repo", [], [])

        self.assertEqual(result, (2, 1, 1))
        self.assertEqual(mocked.call_count, 1)


if __name__ == "__main__":
    unittest.main()

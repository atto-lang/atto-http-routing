import unittest
from reference.route_matcher import RouteError, compile_route, match_route


class RouteMatcherTest(unittest.TestCase):
    def test_static_and_parameter_routes(self):
        self.assertEqual(match_route("/", "/"), {})
        self.assertEqual(match_route("/users/:user_id", "/users/abc_123"),
                         {"user_id": "abc_123"})
        self.assertEqual(match_route("/users/:user_id", "/groups/abc_123"), None)
        self.assertEqual(match_route("/users/:user_id", "/users/1/extra"), None)
        self.assertEqual(compile_route("/v1/:id"), ("v1", ":id"))

    def test_reject_ambiguous_and_unsafe_routes(self):
        for pattern, path in [
            ("/:id/:id", "/a/b"), ("/:Bad", "/a"), ("/x//y", "/x/a"),
            ("/:id", "/%2F"), ("/x", "/x?other"), ("/x", "/x/.."),
            ("/x", "/x/"), ("/x", "/x#y")
        ]:
            with self.subTest(pattern=pattern, path=path), self.assertRaises(RouteError):
                match_route(pattern, path)

    def test_path_is_not_percent_decoded(self):
        with self.assertRaises(RouteError):
            match_route("/:name", "/hello%20world")


if __name__ == "__main__":
    unittest.main()

import unittest

from protocol import parse_uid_line


class ProtocolTests(unittest.TestCase):
    def test_normalizes_supported_uid_sizes(self):
        for value in ("UID:04a1b2c3", "UID:04a1b2c3d4e5f6", "UID:04a1b2c3d4e5f6071829"):
            self.assertEqual(parse_uid_line(value + "\r\n"), value[4:].upper())

    def test_rejects_malformed_or_unsupported_lines(self):
        for value in ("", "04A1B2C3", "UID:xyz", "UID:1234", "UID:04a1b2c3extra", "UID:04a1b2c3\nUID:04a1b2c3"):
            self.assertIsNone(parse_uid_line(value))


if __name__ == "__main__":
    unittest.main()

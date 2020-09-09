import unittest
from unittest.mock import patch

from securedrop.client import Client
import os
import json


sd_filename = 'securedrop.json'


class InputSideEffect:
    i = 0
    lt: list

    def __init__(self, lst):
        self.lt = lst

    def se(self, *args, **kwargs):
        val = self.lt[self.i]
        self.i += 1
        return val


class TestRegistration(unittest.TestCase):
    def test_aaa_initial_ask_to_register_no_response_fails(self):
        se = InputSideEffect(["n"])
        with patch('builtins.input', side_effect=se.se):
            with self.assertRaises(RuntimeError):
                Client(sd_filename)

    def test_aab_initial_registration_succeeds(self):
        se1 = InputSideEffect(["y", "name_v", "email_v"])
        se2 = InputSideEffect(["password_v", "password_v"])
        with patch('builtins.input', side_effect=se1.se):
            with patch('getpass.getpass', side_effect=se2.se):
                Client(sd_filename)

    def assert_initial_registered_users_dict_is_valid(self, d):
        for email, cd in d.items():
            self.assertEqual(email, "email_v")
            self.assertEqual(cd["email"], email)
            self.assertEqual(cd["name"], "name_v")
            self.assertTrue(not cd["contacts"])
            self.assertTrue(cd["auth"]["salt"])
            self.assertTrue(cd["auth"]["key"])

    def assert_initial_registered_users_is_valid(self, ru):
        for email, cd in ru.items():
            self.assertEqual(email, "email_v")
            self.assertEqual(cd.email, email)
            self.assertEqual(cd.name, "name_v")
            self.assertTrue(not cd.contacts)
            self.assertTrue(cd.auth.salt)
            self.assertTrue(cd.auth.key)

    def test_aac_initial_json_valid(self):
        with open(sd_filename, 'r') as f:
            jdict = json.load(f)
            self.assert_initial_registered_users_dict_is_valid(jdict)

    def test_aad_initial_load_from_json(self):
        client = Client(sd_filename)
        self.assert_initial_registered_users_is_valid(client.users.users)


if __name__ == '__main__':
    if os.path.exists(sd_filename):
        os.remove(sd_filename)
    unittest.main()

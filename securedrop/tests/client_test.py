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

    # Test prefix aaa, aab, etc. is to ensure the tests run in the correct order

    def test_aaa_initial_ask_to_register_no_response_fails(self):
        """Ensures that client throws if the user declines to register a user."""
        se = InputSideEffect(["n", "exit"])
        with patch('builtins.input', side_effect=se.se):
            with self.assertRaises(RuntimeError):
                Client(sd_filename)

    def test_aab_initial_ask_to_register_mismatching_passwords(self):
        """Ensures that client throws if the user inputs mismatching passwords during registration."""
        se1 = InputSideEffect(["y", "name_v", "email_v", "exit"])
        se2 = InputSideEffect(["password_v", "password_v_"])
        with patch('builtins.input', side_effect=se1.se):
            with patch('getpass.getpass', side_effect=se2.se):
                with self.assertRaises(RuntimeError):
                    Client(sd_filename)

    def test_aac_initial_ask_to_register_empty_input(self):
        """Ensures that client throws if the user inputs an empty string during registration."""
        for i in range(0, 2):
            for j in range(0, 2):
                se_lists = [["y", "name_v", "email_v", "exit"], ["password_v", "password_v_"]]
                se_lists[i][j + int(i == 0)] = ""
                se1 = InputSideEffect(se_lists[0])
                se2 = InputSideEffect(se_lists[1])
                with patch('builtins.input', side_effect=se1.se):
                    with patch('getpass.getpass', side_effect=se2.se):
                        with self.assertRaises(RuntimeError):
                            Client(sd_filename)

    def test_aad_initial_registration_succeeds(self):
        """Ensures that client doesn't throw during valid registration."""
        se1 = InputSideEffect(["y", "name_v", "email_v", "exit"])
        se2 = InputSideEffect(["password_v", "password_v"])
        with patch('builtins.input', side_effect=se1.se):
            with patch('getpass.getpass', side_effect=se2.se):
                Client(sd_filename)

    def assert_initial_registered_users_dict_is_valid(self, d):
        for email, cd in d.items():
            self.assertEqual(email, "05c0f2ea8e3967a16d55bc8894d3787a69d3821d327f687863e6492cb74654c3")
            self.assertEqual(cd["email"], email)
            self.assertTrue(cd["name"], ["data"])
            self.assertTrue(cd["name"], ["verify"])
            self.assertTrue(cd["contacts"]["data"])
            self.assertTrue(cd["contacts"]["verify"])
            self.assertTrue(cd["auth"]["salt"])
            self.assertTrue(cd["auth"]["key"])

    def assert_initial_registered_users_is_valid(self, ru):
        for email, cd in ru.items():
            self.assertEqual(email, "05c0f2ea8e3967a16d55bc8894d3787a69d3821d327f687863e6492cb74654c3")
            self.assertEqual(cd.email_hash, "05c0f2ea8e3967a16d55bc8894d3787a69d3821d327f687863e6492cb74654c3")
            self.assertTrue(cd.auth.salt)
            self.assertTrue(cd.auth.key)

    def test_aae_initial_json_valid(self):
        """Ensures that client serializes to JSON correctly after registration."""
        with open(sd_filename, 'r') as f:
            jdict = json.load(f)
            self.assert_initial_registered_users_dict_is_valid(jdict)

    def test_aaf_initial_load_from_json(self):
        """Ensures that client deserializes from JSON correctly."""
        client = Client(sd_filename)
        self.assert_initial_registered_users_is_valid(client.users.users)

    def test_aag_login_unknown_email(self):
        """Ensures that client throws if trying to login with an invalid email."""
        client = Client(sd_filename)
        se1 = InputSideEffect(["email_v_"])
        se2 = InputSideEffect(["password_v"])
        with patch('builtins.input', side_effect=se1.se):
            with patch('getpass.getpass', side_effect=se2.se):
                with self.assertRaises(RuntimeError):
                    client.login()

    def test_aah_login_wrong_password(self):
        """Ensures that client throws if trying to login with an invalid password."""
        client = Client(sd_filename)
        se1 = InputSideEffect(["email_v"])
        se2 = InputSideEffect(["password_v_"])
        with patch('builtins.input', side_effect=se1.se):
            with patch('getpass.getpass', side_effect=se2.se):
                with self.assertRaises(RuntimeError):
                    client.login()

    def test_aai_login_correct_password(self):
        """Ensures that client logs in successfully with correct email/password."""
        client = Client(sd_filename)
        se1 = InputSideEffect(["email_v", "exit"])
        se2 = InputSideEffect(["password_v"])
        with patch('builtins.input', side_effect=se1.se):
            with patch('getpass.getpass', side_effect=se2.se):
                client.login()

    def test_aaj_add_contact_empty_input(self):
        """Ensures that client does not add a new contact if the input is an empty string."""
        client = Client(sd_filename)
        for i in range(0, 2):
            se_list = ["email_v", "add", "name_v_2", "email_v_2", "exit"]
            se_list[2 + i] = ""
            se1 = InputSideEffect(se_list)
            se2 = InputSideEffect(["password_v"])
            with patch('builtins.input', side_effect=se1.se):
                with patch('getpass.getpass', side_effect=se2.se):
                    client.login()
                    self.assertTrue("email_v_2" not in client.users.users["05c0f2ea8e3967a16d55bc8894d3787a69d3821d327f687863e6492cb74654c3"].contacts)

    def test_aak_add_contact(self):
        """Ensures that client adds valid contacts successfully."""
        client = Client(sd_filename)
        se1 = InputSideEffect(["email_v", "add", "name_v_2", "email_v_2", "add", "name_v_3", "email_v_3", "exit"])
        se2 = InputSideEffect(["password_v"])
        with patch('builtins.input', side_effect=se1.se):
            with patch('getpass.getpass', side_effect=se2.se):
                client.login()
                self.assertEqual(client.users.users["05c0f2ea8e3967a16d55bc8894d3787a69d3821d327f687863e6492cb74654c3"].contacts["email_v_2"], "name_v_2")
                self.assertEqual(client.users.users["05c0f2ea8e3967a16d55bc8894d3787a69d3821d327f687863e6492cb74654c3"].contacts["email_v_3"], "name_v_3")


if __name__ == '__main__':
    if os.path.exists(sd_filename):
        os.remove(sd_filename)
    unittest.main()

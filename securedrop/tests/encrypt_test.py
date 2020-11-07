import unittest
from unittest.mock import patch

from securedrop.client import Client, ClientData
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

    def test_aaa_initial_registration_succeeds(self):
        """Ensures that client doesn't throw during valid registration."""
        se1 = InputSideEffect(["y", "Testname", "email_v", "exit"])
        se2 = InputSideEffect(["password_v", "password_v"])
        with patch('builtins.input', side_effect=se1.se):
            with patch('getpass.getpass', side_effect=se2.se):
                Client(sd_filename)

    def test_aab_login_correct_password(self):
        """Ensures that client logs in successfully with correct email/password."""
        client = Client(sd_filename)
        se1 = InputSideEffect(["email_v", "exit"])
        se2 = InputSideEffect(["password_v"])
        with patch('builtins.input', side_effect=se1.se):
            with patch('getpass.getpass', side_effect=se2.se):
                client.login()

    def test_aac_add_contacts_hashed_email(self):
        """Ensures that client adds valid contacts successfully, and that we can decrypt them."""
        client = Client(sd_filename)
        se1 = InputSideEffect(["email_v", "add", "name_v_2", "email_v_2", "add", "name_v_3", "email_v_3", "exit"])
        se2 = InputSideEffect(["password_v"])
        with patch('builtins.input', side_effect=se1.se):
            with patch('getpass.getpass', side_effect=se2.se):
                client.login()
                user = client.users.users["05c0f2ea8e3967a16d55bc8894d3787a69d3821d327f687863e6492cb74654c3"]
                self.assertEqual(user.contacts["email_v_2"], "name_v_2")
                self.assertEqual(user.contacts["email_v_3"], "name_v_3")

    def test_aad_login_correct_password_decrypt_contact(self):
        """Ensures that client logs in successfully with correct email/password Then decrypts contacts."""
        client = Client(sd_filename)
        user = client.users.users["05c0f2ea8e3967a16d55bc8894d3787a69d3821d327f687863e6492cb74654c3"]
        user.email = "email_v"
        self.assertNotEqual(user.enc_contacts, "name_v_3")
        user.decrypt_name_contacts()
        self.assertIsNotNone(user.contacts)
        self.assertEqual(user.contacts["email_v_2"], "name_v_2")
        self.assertEqual(user.contacts["email_v_3"], "name_v_3")

    def test_aae_data_in_memory_after_decrypt(self):
        """Ensures that Client data can be accessed in local memory after decryption"""
        client = Client(sd_filename)
        user = client.users.users["05c0f2ea8e3967a16d55bc8894d3787a69d3821d327f687863e6492cb74654c3"]
        user.email = "email_v"
        user.decrypt_name_contacts()
        self.assertEqual(user.name, "Testname")
        self.assertEqual(user.contacts["email_v_2"], "name_v_2")
        self.assertEqual(user.contacts["email_v_3"], "name_v_3")

    def test_aaf_test_decrypt_wrong_password(self):
        """Ensures that client throws an error when decryption is not successful (wrong key)."""
        client = Client(sd_filename)
        user = client.users.users["05c0f2ea8e3967a16d55bc8894d3787a69d3821d327f687863e6492cb74654c3"]
        user.email = "email_v_"
        with self.assertRaises(RuntimeError):
            user.decrypt_name_contacts()
        user.email = ""
        with self.assertRaises(RuntimeError):
            user.decrypt_name_contacts()


if __name__ == '__main__':
    if os.path.exists(sd_filename):
        os.remove(sd_filename)
    unittest.main()

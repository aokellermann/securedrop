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

    def test_aad_initial_registration_succeeds(self):
        """Ensures that client doesn't throw during valid registration."""
        se1 = InputSideEffect(["y", "Testname", "email_v", "exit"])
        se2 = InputSideEffect(["password_v", "password_v"])
        with patch('builtins.input', side_effect=se1.se):
            with patch('getpass.getpass', side_effect=se2.se):
                Client(sd_filename)

    def test_aai_login_correct_password(self):
        """Ensures that client logs in successfully with correct email/password."""
        client = Client(sd_filename)
        se1 = InputSideEffect(["email_v", "exit"])
        se2 = InputSideEffect(["password_v"])
        with patch('builtins.input', side_effect=se1.se):
            with patch('getpass.getpass', side_effect=se2.se):
                client.login()

    def test_aak_add_contact(self):
        """Ensures that client adds valid contacts successfully."""
        client = Client(sd_filename)
        se1 = InputSideEffect(["email_v", "add", "name_v_2", "email_v_2", "add", "name_v_3", "email_v_3", "exit"])
        se2 = InputSideEffect(["password_v"])
        with patch('builtins.input', side_effect=se1.se):
            with patch('getpass.getpass', side_effect=se2.se):
                client.login()
                self.assertIsNot(client.users.users["email_v"], "name_v_2")
                self.assertIsNot(client.users.users["email_v"], "name_v_3")
                user = client.users.users["email_v"]

    def test_aal_initial_registration_succeeds(self):
        """Ensures that data can be encrypted and then decryped and read again"""
        user = ClientData(nm="name_t", em="email_t", password="password_t")
        self.assertEqual(user.name, "name_t")
        self.assertEqual(user.email, "email_t")
        user.encrypt("password_t")
        user.decrypt('password_t')
        self.assertEqual(user.name, "name_t")
        self.assertEqual(user.email, "email_t")



if __name__ == '__main__':
    if os.path.exists(sd_filename):
        os.remove(sd_filename)
    unittest.main()

#!/usr/bin/env python3

import os
import unittest
from unittest.mock import patch

import securedrop.client as client
from securedrop.client import LIST_CONTACTS_TEST_FILENAME
from securedrop.server import ServerDriver, Server, DEFAULT_filename, AESWrapper
import json
import time
import contextlib

from multiprocessing import shared_memory, Process


class InputSideEffect:
    i = 0
    lt: list

    def __init__(self, lst):
        self.lt = lst

    def se(self, *args, **kwargs):
        val = self.lt[self.i]
        self.i += 1
        return val


@contextlib.contextmanager
def server_process():
    with ServerDriver() as driver:
        process = Process(target=driver.run)
        try:
            process.start()
            time.sleep(1)
            yield process
        finally:
            sentinel = shared_memory.SharedMemory(driver.sentinel_name())
            sentinel.buf[0] = 1
            sentinel.close()
            process.join()


class TestRegistration(unittest.TestCase):

    # Test prefix aaa, aab, etc. is to ensure the tests run in the correct order

    def test_aaa_initial_ask_to_register_no_response_fails(self):
        """Ensures that client throws if the user declines to register a user."""
        with server_process():
            se = InputSideEffect(["n", "exit"])
            with patch('builtins.input', side_effect=se.se):
                with self.assertRaises(RuntimeError):
                    client.main()

    def test_aab_initial_ask_to_register_mismatching_passwords(self):
        """Ensures that client throws if the user inputs mismatching passwords during registration."""
        with server_process():
            se1 = InputSideEffect(["y", "name_v", "email_v@test.com", "exit"])
            se2 = InputSideEffect(["password_v12", "password_v12_"])
            with patch('builtins.input', side_effect=se1.se):
                with patch('getpass.getpass', side_effect=se2.se):
                    with self.assertRaises(RuntimeError):
                        client.main()

    def test_aac_initial_ask_to_register_empty_input(self):
        """Ensures that client throws if the user inputs an empty string during registration."""
        with server_process():
            for i in range(0, 2):
                for j in range(0, 2):
                    se_lists = [["y", "name_v", "email_v@test.com", "exit"], ["password_v12", "password_v12"]]
                    se_lists[i][j + int(i == 0)] = ""
                    se1 = InputSideEffect(se_lists[0])
                    se2 = InputSideEffect(se_lists[1])
                    with patch('builtins.input', side_effect=se1.se):
                        with patch('getpass.getpass', side_effect=se2.se):
                            with self.assertRaises(RuntimeError):
                                client.main()

    def test_aad_initial_ask_to_register_invalid_email(self):
        """Ensures that client throws if the user inputs invalid email during registration."""
        with server_process():
            invalid_emails = [
                "Abc.example.com", "A@b@c@example.com", "a\"b(c)d,e:f;g<h>i[j\\k]l@example.com",
                "just\"not\"right@example.com", "this is\"not\\allowed@example.com",
                "this\\ still\\\"not\\\\allowed@example.com",
                "1234567890123456789012345678901234567890123456789012345678901234+x@example.com",
                "i_like_underscore@but_its_not_allow_in_this_part.example.com"
            ]
            for i in invalid_emails:
                se1 = InputSideEffect(["y", "name_v", i, "exit"])
                se2 = InputSideEffect(["password_v12", "password_v12"])
                with patch('builtins.input', side_effect=se1.se):
                    with self.assertRaises(RuntimeError):
                        with patch('getpass.getpass', side_effect=se2.se):
                            client.main()

    def test_aae_initial_ask_to_register_password_too_short(self):
        """Ensures that client throws if the user inputs a password that is too short during registration."""
        with server_process():
            se1 = InputSideEffect(["y", "name_v", "email_v", "exit"])
            se2 = InputSideEffect(["password_v1", "password_v1"])
            with patch('builtins.input', side_effect=se1.se):
                with patch('getpass.getpass', side_effect=se2.se):
                    with self.assertRaises(RuntimeError):
                        client.main()

    def test_aaf_initial_registration_succeeds(self):
        """Ensures that client doesn't throw during some wild, yet valid user registrations."""
        valid_emails = [
            "simple@example.com", "very.common@example.com", "x@example.com", "user%example.com@example.org",
            "mailhost!username@example.org", "user.name+tag+sorting@example.com", "fully-qualified-domain@example.com",
            "example-indeed@strange-example.com", "other.email-with-hyphen@example.com",
            "EXTREMELYLONGEMAIL12345678901234567890123456789012345678901234+x@example.com"
        ]
        with server_process():
            for i in valid_emails:
                se1 = InputSideEffect(["y", "name_v", i, "exit"])
                se2 = InputSideEffect(["password_v12", "password_v12"])
                with patch('builtins.input', side_effect=se1.se):
                    with patch('getpass.getpass', side_effect=se2.se):
                        client.main()
                        os.remove(client.DEFAULT_FILENAME)
                        os.remove(DEFAULT_filename)

    def test_aag_initial_registration_succeeds(self):
        """Ensures that client doesn't throw during valid registration."""
        with server_process():
            se1 = InputSideEffect(["y", "name_v", "email_v@test.com", "exit"])
            se2 = InputSideEffect(["password_v12", "password_v12"])
            with patch('builtins.input', side_effect=se1.se):
                with patch('getpass.getpass', side_effect=se2.se):
                    client.main()

    def assert_initial_registered_users_dict_is_valid(self, d):
        for email, cd in d.items():
            self.assertEqual(email, "e908de13f0f86b9c15f70d34cc1a5696280b3fbf822ae09343a779b19a3214b7")
            self.assertEqual(cd["email"], email)
            self.assertTrue(cd["name"])
            self.assertTrue(cd["contacts"])
            self.assertTrue(cd["auth"]["salt"])
            self.assertTrue(cd["auth"]["key"])

    def assert_initial_registered_users_is_valid(self, ru):
        for email, cd in ru.items():
            self.assertEqual(email, "e908de13f0f86b9c15f70d34cc1a5696280b3fbf822ae09343a779b19a3214b7")
            self.assertEqual(cd.email_hash, "e908de13f0f86b9c15f70d34cc1a5696280b3fbf822ae09343a779b19a3214b7")
            self.assertTrue(cd.auth.salt)
            self.assertTrue(cd.auth.key)

    def test_aah_initial_json_valid(self):
        """Ensures that client serializes to JSON correctly after registration."""
        with open(DEFAULT_filename, 'r') as f:
            jdict = json.load(f)
            self.assert_initial_registered_users_dict_is_valid(jdict)

    def test_aai_initial_load_from_json(self):
        """Ensures that client deserializes from JSON correctly."""
        serv = Server(DEFAULT_filename)
        self.assert_initial_registered_users_is_valid(serv.users.users)

    def test_aaj_login_unknown_email(self):
        """Ensures that client throws if trying to login with an unknown email."""
        with server_process():
            se1 = InputSideEffect(["email_v_@test.com"])
            se2 = InputSideEffect(["password_v12"])
            with patch('builtins.input', side_effect=se1.se):
                with patch('getpass.getpass', side_effect=se2.se):
                    with self.assertRaises(RuntimeError):
                        client.main()

    def test_aak_login_wrong_password(self):
        """Ensures that client throws if trying to login with an incorrect password."""
        with server_process():
            se1 = InputSideEffect(["email_v@test.com"])
            se2 = InputSideEffect(["password_v12_"])
            with patch('builtins.input', side_effect=se1.se):
                with patch('getpass.getpass', side_effect=se2.se):
                    with self.assertRaises(RuntimeError):
                        client.main()

    def test_aal_login_correct_password(self):
        """Ensures that client logs in successfully with correct email/password."""
        with server_process():
            se1 = InputSideEffect(["email_v@test.com", "exit"])
            se2 = InputSideEffect(["password_v12"])
            with patch('builtins.input', side_effect=se1.se):
                with patch('getpass.getpass', side_effect=se2.se):
                    client.main()

    def test_aam_add_contact_empty_input(self):
        """Ensures that client does not add a new contact if the input is an empty string."""
        with server_process():
            for i in range(0, 2):
                se_list = ["email_v@test.com", "add", "name_v_2", "email_v_2@test.com", "exit"]
                se_list[2 + i] = ""
                se1 = InputSideEffect(se_list)
                se2 = InputSideEffect(["password_v12"])
                with patch('builtins.input', side_effect=se1.se):
                    with patch('getpass.getpass', side_effect=se2.se):
                        client.main()
                        with open(DEFAULT_filename, 'r') as f:
                            jdict = json.load(f)
                            contacts = json.loads(
                                AESWrapper("email_v@test.com").decrypt(
                                    jdict["e908de13f0f86b9c15f70d34cc1a5696280b3fbf822ae09343a779b19a3214b7"]
                                    ["contacts"]))
                            self.assertEqual(dict(), contacts)

    def test_aan_add_contact_invalid_email(self):
        """Ensures that client does not add a new contact if the input is an invalid email."""
        invalid_emails = [
            "Abc.example.com", "A@b@c@example.com", "a\"b(c)d,e:f;g<h>i[j\\k]l@example.com",
            "just\"not\"right@example.com", "this is\"not\\allowed@example.com",
            "this\\ still\\\"not\\\\allowed@example.com",
            "1234567890123456789012345678901234567890123456789012345678901234+x@example.com",
            "i_like_underscore@but_its_not_allow_in_this_part.example.com"
        ]
        with server_process():
            for i in invalid_emails:
                se_list = ["email_v@test.com", "add", "name_v_2", i, "exit"]
                se_list[3] = i
                se1 = InputSideEffect(se_list)
                se2 = InputSideEffect(["password_v12"])
                with patch('builtins.input', side_effect=se1.se):
                    with patch('getpass.getpass', side_effect=se2.se):
                        client.main()
                        with open(DEFAULT_filename, 'r') as f:
                            jdict = json.load(f)
                            contacts = json.loads(
                                AESWrapper("email_v@test.com").decrypt(
                                    jdict["e908de13f0f86b9c15f70d34cc1a5696280b3fbf822ae09343a779b19a3214b7"]
                                    ["contacts"]))
                            self.assertEqual(dict(), contacts)

    def test_aao_add_contact(self):
        """Ensures that client adds valid contacts successfully."""
        with server_process():
            se1 = InputSideEffect([
                "email_v@test.com", "add", "name_v_2", "email_v_2@test.com", "add", "name_v_3", "email_v_3@test.com",
                "exit"
            ])
            se2 = InputSideEffect(["password_v12"])
            with patch('builtins.input', side_effect=se1.se):
                with patch('getpass.getpass', side_effect=se2.se):
                    client.main()
                    with open(DEFAULT_filename, 'r') as f:
                        jdict = json.load(f)
                        contacts = json.loads(
                            AESWrapper("email_v@test.com").decrypt(
                                jdict["e908de13f0f86b9c15f70d34cc1a5696280b3fbf822ae09343a779b19a3214b7"]["contacts"]))
                        self.assertEqual("name_v_2", contacts["email_v_2@test.com"])
                        self.assertEqual("name_v_3", contacts["email_v_3@test.com"])

    def test_aap_list_contacts_empty_dictionary(self):
        """Ensures that does not list users if no users have been added"""
        with server_process():
            se1 = InputSideEffect(["email_v@test.com", "list", "exit"])
            se2 = InputSideEffect(["password_v12"])
            with patch('builtins.input', side_effect=se1.se):
                with patch('getpass.getpass', side_effect=se2.se):
                    client.main(None, None, None, True)
                    with open(LIST_CONTACTS_TEST_FILENAME, 'r') as f:
                        jdict = json.load(f)
                        is_empty = not bool(jdict)
                        self.assertTrue(is_empty)

    def test_aaq_login_correct_password_decrypt_contact(self):
        """Ensures that client logs in successfully with correct email/password Then decrypts contacts."""
        server = Server(DEFAULT_filename)
        user = server.users.users["e908de13f0f86b9c15f70d34cc1a5696280b3fbf822ae09343a779b19a3214b7"]
        user.email = "email_v@test.com"
        self.assertNotEqual(user.enc_contacts, "name_v_3")
        user.decrypt_name_contacts()
        self.assertIsNotNone(user.contacts)
        self.assertEqual(user.contacts["email_v_2@test.com"], "name_v_2")
        self.assertEqual(user.contacts["email_v_3@test.com"], "name_v_3")

    def test_aar_data_in_memory_after_decrypt(self):
        """Ensures that Client data can be accessed in local memory after decryption"""
        server = Server(DEFAULT_filename)
        user = server.users.users["e908de13f0f86b9c15f70d34cc1a5696280b3fbf822ae09343a779b19a3214b7"]
        user.email = "email_v@test.com"
        user.decrypt_name_contacts()
        self.assertEqual(user.name, "name_v")
        self.assertEqual(user.contacts["email_v_2@test.com"], "name_v_2")
        self.assertEqual(user.contacts["email_v_3@test.com"], "name_v_3")

    def test_aas_test_decrypt_wrong_password(self):
        """Ensures that client throws an error when decryption is not successful (wrong key)."""
        server = Server(DEFAULT_filename)
        user = server.users.users["e908de13f0f86b9c15f70d34cc1a5696280b3fbf822ae09343a779b19a3214b7"]
        user.email = "email_v_@test.com"
        with self.assertRaises(RuntimeError):
            user.decrypt_name_contacts()


if __name__ == '__main__':
    unittest.main()

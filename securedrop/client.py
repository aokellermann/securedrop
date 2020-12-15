#!/usr/bin/env python3
import getpass
import json
import os
import select
import sys
import time
from multiprocessing import Process, shared_memory, Lock
from threading import Thread

import nest_asyncio

from securedrop import utils
from securedrop.List_Contacts_Packets import ListContactsPackets
from securedrop.List_Contacts_Response_Packets import ListContactsResponsePackets
from securedrop.add_contact_packets import AddContactPackets
from securedrop.client_server_base import ClientBase
from securedrop.file_transfer_packets import FileTransferRequestPackets, FileTransferRequestResponsePackets, \
    FileTransferCheckRequestsPackets, FileTransferAcceptRequestPackets, FileTransferSendTokenPackets, \
    FileTransferSendPortPackets, FileTransferSendPortTokenPackets, FILE_TRANSFER_P2P_CHUNK_SIZE
from securedrop.login_packets import LoginPackets
from securedrop.p2p import P2PClient, P2PServer
from securedrop.register_packets import RegisterPackets
from securedrop.status_packets import StatusPackets
from securedrop.utils import sha256_file, sizeof_fmt
from securedrop.utils import validate_and_normalize_email

DEFAULT_FILENAME = 'client.json'
LIST_CONTACTS_TEST_FILENAME = 'list_contacts_test.json'
DEFAULT_HOSTNAME = '127.0.0.1'
DEFAULT_PORT = 6969
DEBUG_DEFAULT = False
DEBUG = False


class RegisteredUsers:
    def __init__(self, filename):
        self.filename = filename
        self.users = set()
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                self.users = set(json.load(f))

    def make_json(self):
        return list(self.users)

    def write_json(self):
        with open(self.filename, 'w') as f:
            json.dump(self.make_json(), f)

    def register_prompt(self):
        name = input("Enter Full Name: ")
        email = input("Enter Email Address: ")
        valid_email = validate_and_normalize_email(email)
        if valid_email is None:
            raise RuntimeError("Invalid Email Address.")
        if valid_email in self.users:
            raise RuntimeError("That email already exists!")

        pw1 = getpass.getpass(prompt="Enter Password: ")
        pw2 = getpass.getpass(prompt="Re-enter password: ")
        if pw1 != pw2:
            raise RuntimeError("The two entered passwords don't match!")

        # enforce password length to min of 12 characters
        if len(pw1) < 12:
            raise RuntimeError("Password is too short! Password must be at least 12 characters")

        if not name or not valid_email or not pw1:
            raise RuntimeError("Empty input")

        return name, valid_email, pw1

    def register_user(self, email):
        self.users.add(email)
        self.write_json()
        print("User registered.")

    def login_prompt(self):
        email = input("Enter Email Address: ")
        password = getpass.getpass(prompt="Enter Password: ")
        return email, password


class Client(ClientBase):
    users: RegisteredUsers

    def __init__(self, host: str, prt: int, filename):
        super().__init__(host, prt)
        self.filename = filename
        try:
            self.users = RegisteredUsers(filename)
            self.user = None
        except Exception as e:
            print("Exiting SecureDrop")
            raise e

    async def main(self, server_cert_path="server.pem"):
        try:
            await super().main()

            if not self.users.users:
                decision = input(
                    "No users are registered with this client.\nDo you want to register a new user (y/n)? ")
                if str(decision) == 'y':
                    self.user = await self.register()
                    if self.user:
                        await self.sh()
                    else:
                        raise RuntimeError("Registration failed.")
                else:
                    raise RuntimeError("You must register a user before using securedrop")
            else:
                self.user = await self.login()
                if self.user:
                    await self.sh()
                else:
                    raise RuntimeError("Login failed.")
        except KeyboardInterrupt:
            pass
        except RuntimeError as e:
            print(e)
        finally:
            print("Exiting SecureDrop")

    async def register(self):
        msg, email = None, None
        try:
            name, email, pw = self.users.register_prompt()
            await self.write(bytes(RegisterPackets(name, email, pw)))
            msg = StatusPackets(data=(await self.read())[4:]).message
            if msg != "":
                raise RuntimeError(msg)
            self.users.register_user(email)
        except RuntimeError as e:
            msg = str(e)
        if msg != "":
            print("Failed to register: ", msg)
            return None
        return email

    async def login(self):
        msg, email = None, None
        try:
            email, pw = self.users.login_prompt()
            await self.write(bytes(LoginPackets(email, pw)))
            msg = StatusPackets(data=(await self.read())[4:]).message
            if msg != "":
                raise RuntimeError(msg)
        except RuntimeError as e:
            msg = str(e)
        if msg != "":
            print("Failed to login: ", msg)
            return None
        return email

    async def sh(self):
        try:
            print("Welcome to SecureDrop")
            print("Type \"help\" For Commands")
            prompt = True
            while True:
                if prompt:
                    print("secure_drop> ", end="", flush=True)
                    prompt = False
                if select.select([sys.stdin], [], [], 1)[0]:
                    cmd = input().strip()
                    if cmd == "help":
                        print("\"add\"  \t-> Add a new contact")
                        print("\"list\"  \t-> List all online contacts")
                        print("\"send\"  \t-> Transfer file to contact")
                        print("\"exit\"  \t-> Exit SecureDrop")
                    elif cmd == "add":
                        await self.add_contact()
                    elif cmd == "list":
                        await self.list_contacts()
                    elif cmd == "send":
                        await self.send_file()
                    elif cmd == "exit":
                        break
                    else:
                        print("Unknown command: {}".format(cmd))
                    prompt = True

                if (await self.check_for_file_transfer_requests()) is not None:
                    prompt = True
        except Exception or KeyboardInterrupt as e:
            print("Exiting SecureDrop")
            raise e

    async def add_contact(self):
        msg = None
        try:
            name = input("Enter Full Name: ")
            email = input("Enter Email Address: ")
            valid_email = validate_and_normalize_email(email)
            if valid_email is None:
                raise RuntimeError("Invalid Email Address.")
            if not name:
                raise RuntimeError("Empty name input.")

            await self.write(bytes(AddContactPackets(name, valid_email)))
            msg = StatusPackets(data=(await self.read())[4:]).message
            if msg != "":
                raise RuntimeError(msg)
        except RuntimeError as e:
            msg = str(e)
        if msg != "":
            print("Failed to add contact: ", msg)

    async def list_contacts(self):
        msg = ""
        try:
            await self.write(bytes(ListContactsPackets()))
            contact_dict = ListContactsResponsePackets(data=(await self.read())[4:]).contacts
            # print contacts by Email and Name
            if len(contact_dict) > 0:
                print("Email:\t\t\t\tName:")
                for email, name in contact_dict.items():
                    print(email + "\t\t\t" + name)
            else:
                print("No contacts online!")

            if DEBUG:
                try:
                    with open(LIST_CONTACTS_TEST_FILENAME, 'w') as f:
                        json.dump(contact_dict, f)
                except RuntimeError as e:
                    msg = str(e)

        except RuntimeError as e:
            msg = str(e)

        if msg != "":
            print("Failed to list contacts: ", msg)

    # Y
    async def check_for_file_transfer_requests(self):
        # 2. `Y -> S`: every one second, Y asks server for any requests
        await self.write(bytes(FileTransferRequestResponsePackets()))

        # 3. `S -> X/F -> Y`: server responds with active requests
        file_transfer_requests = FileTransferCheckRequestsPackets(data=(await self.read())[4:]).requests
        if not file_transfer_requests:
            return

        print("Incoming file transfer request(s):")
        index_to_email = dict()
        index_to_file_info = dict()
        i = 1
        for email, file_info in file_transfer_requests.items():
            print("\t{}. {}".format(i, email))
            print("\t\tname: ", file_info["name"])
            print("\t\tsize: ", sizeof_fmt(int(file_info["size"])))
            print("\t\tSHA256: ", file_info["SHA256"])
            index_to_email[i] = email
            index_to_file_info[i] = file_info
            i += 1

        try:
            selection = input("\nEnter the number for which request you'd like to accept, or 0 to deny all: ")
            accept = True
            selection_num = int(selection)
            if selection_num <= 0 or selection_num >= i:
                raise ValueError

            packets = FileTransferAcceptRequestPackets(index_to_email[selection_num])
        except ValueError or KeyboardInterrupt:
            packets = FileTransferAcceptRequestPackets("")
            accept = False

        if accept:
            while True:
                out_directory = input("Enter the output directory: ")
                file_path = os.path.join(out_directory, index_to_file_info[selection_num]["name"])
                if not os.path.isdir(out_directory):
                    print("The path {} is not a directory".format(os.path.abspath(out_directory)))
                elif os.path.exists(file_path):
                    print("The file {} already exists".format(file_path))
                else:
                    break

        # 4. `Y -> Yes/No -> S`: Y accepts or denies transfer request
        await self.write(bytes(packets))
        if not accept:
            return False

        # 5. `S -> Token -> Y`: if Y accepted, server sends a unique token Y
        token = FileTransferSendTokenPackets(data=(await self.read())[4:]).token

        lock = Lock()
        progress = shared_memory.SharedMemory(create=True, size=8)
        sentinel = shared_memory.SharedMemory(create=True, size=1)
        listen_port = shared_memory.SharedMemory(create=True, size=4)

        # 6. `Y -> Port -> S`: Y binds to 0 (OS chooses) and sends the port it's listening on to S
        p2p_server = P2PServer(token, os.path.abspath(out_directory), progress.name, lock, listen_port.name)
        p2p_server_process = Process(target=p2p_server.run, args=(
            0,
            sentinel.name,
        ))
        p2p_server_process.start()

        print("Started P2P server. Waiting for listen...")

        # wait for listen
        port = 0
        while port == 0:
            with lock:
                port = int.from_bytes(listen_port.buf, byteorder='little')

        await self.write(bytes(FileTransferSendPortPackets(port)))

        # Wait until file received

        time_start = time.time()
        status_sentinel = False

        chunk_size = FILE_TRANSFER_P2P_CHUNK_SIZE

        def print_received_progress():
            while not status_sentinel:
                with lock:
                    utils.print_status(*utils.get_progress(int.from_bytes(progress.buf[0:4], byteorder='little'),
                                                           int.from_bytes(progress.buf[4:8], byteorder='little'),
                                                           chunk_size), "received")
                time.sleep(0.03)
            print()

        status_thread = Thread(target=print_received_progress)
        status_thread.start()
        try:
            p2p_server_process.join()
        except KeyboardInterrupt:
            raise RuntimeError("User requested abort")
        finally:
            if p2p_server_process.is_alive():
                p2p_server_process.terminate()
            status_sentinel = True
            status_thread.join()
            print_received_progress()
            progress.close()
            progress.unlink()
            sentinel.close()
            sentinel.unlink()
            listen_port.close()
            listen_port.unlink()

            time_end = time.time()

        print("File transfer completed successfully in {} seconds.".format(time_end - time_start))
        return True

    # X
    async def send_file(self):
        msg = None
        try:
            # 1. `X -> Y/F -> S`: X wants to send F to Y

            recipient_email = input("Enter the recipient's email address: ")
            file_path = os.path.abspath(input("Enter the file path: "))
            valid_email = validate_and_normalize_email(recipient_email)
            if valid_email is None:
                raise RuntimeError("Invalid Email Address.")
            if not file_path:
                raise RuntimeError("Empty file path.")
            if not os.path.exists(file_path):
                raise RuntimeError("Cannot find file: {}".format(file_path))
            if not os.path.isfile(file_path):
                raise RuntimeError("Not a file: {}".format(file_path))

            file_base = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            file_sha256 = sha256_file(file_path)
            file_info = {
                "name": file_base,
                "size": file_size,
                "SHA256": file_sha256,
            }

            # send request
            await self.write(bytes(FileTransferRequestPackets(valid_email, file_info)))

            # this only checks if the request is valid
            # this does not check if the recipient accepted or denied the request
            msg = StatusPackets(data=(await self.read())[4:]).message
            if msg != "":
                raise RuntimeError(msg)

            # 7. `S -> Token/Port -> X`: S sends the same token and port to X

            # denied request is indicated by empty token and port
            port_and_token = FileTransferSendPortTokenPackets(data=(await self.read())[4:])
            port, token = port_and_token.port, port_and_token.token
            if token and port:
                print("User {} accepted the file transfer Connecting to recipient on port ".format(valid_email, port))
            else:
                raise RuntimeError("User {} declined the file transfer request".format(valid_email))

            progress = shared_memory.SharedMemory(create=True, size=8)
            progress_lock = Lock()
            p2p_client = P2PClient(port, token, file_path, file_size, file_sha256, progress.name, progress_lock)

            time_start = time.time()
            sentinel = False

            chunk_size = FILE_TRANSFER_P2P_CHUNK_SIZE

            def print_sent_progress():
                while not sentinel:
                    with progress_lock:
                        utils.print_status(*utils.get_progress(int.from_bytes(progress.buf[0:4], byteorder='little'),
                                                               int.from_bytes(progress.buf[4:8], byteorder='little'),
                                                               chunk_size), "sent")
                    time.sleep(0.03)
                print()

            # i was having trouble with asyncio.gather, so just run status printer in a new thread
            status_thread = Thread(target=print_sent_progress)
            status_thread.start()

            # wait until p2p transfer completes, unless keyboard interrupt
            try:
                await p2p_client.main()
            except KeyboardInterrupt:
                raise RuntimeError("User requested abort")
            finally:
                sentinel = True
                status_thread.join()
                print_sent_progress()
                progress.close()
                progress.unlink()
                time_end = time.time()

            print("\nFile transfer completed in {} seconds.".format(time_end - time_start))

        except RuntimeError as e:
            msg = str(e)
        if msg != "":
            print("Failed to send file: ", msg)


def main(hostname=None, port=None, filename=None, debug=None):
    nest_asyncio.apply()
    hostname = hostname if hostname is not None else DEFAULT_HOSTNAME
    port = port if port is not None else DEFAULT_PORT
    filename = filename if filename is not None else DEFAULT_FILENAME
    global DEBUG
    DEBUG = debug if debug is not None else DEBUG_DEFAULT
    Client(hostname, port, filename).run()


if __name__ == "__main__":
    main()

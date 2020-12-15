# Securedrop

Securedrop is a command line application that facilitates the secure transfer of files between users in a peer-to-peer network.


## Installation

### Clone and Build
```bash
git clone https://github.com/aokellermann/securedrop
cd ./securedrop
python ./scripts/setup.py build
```

### Install dependencies 
```bash
python ./setup.py install
```
## Usage

### Running with no executable arguments

#### Running the server
```bash
./bin/securedrop_server
```
#### Running the client
```bash
./bin/securedrop
```
### Running with executable arguments
#### Running the server
```bash
./bin/securedrop_server --port 6789 --file example_file.json --verbose
```
#### Running the client
```bash
./bin/securedrop --port 6789 --address 127.0.0.1 -f example_file_2.json --verbose 
```

## Code
### Important Files
Key files for this project include: server.py, client.py, client_server_base.py, and p2p.py. 
The server.py file handles the runtime server, authentication, client data, and registered users
from the server side. The client.py file handles registered users on the client side, 
and the client shell. The client_server_base.py file handles the initialization 
(port number, host, etc.) of the client and server objects. 
The p2p.py handles file transfer between users
### Modularity
The project (with its extensive use of classes) takes an object oriented approach to solving key problems. 
As an example of code reusability, see the conventions for the ‘packet’ classes. 
### Readability
The project includes a script (format.sh) which executes the YAPF formatter to maintain a uniform style.
Our team has also engaged in code reviews to maintain good code quality.
### Testing
Securedrop has also been thoroughly tested. From project root, unit tests can be found in the 
./securedrop/tests directory.  

## Security
Below is a list of the security features we implemented
```
* Email Validation
* Password length enforcement 
* Transport Layer Security (TLS)
* HMAC
* AES
* SHA256

```
## License
[MIT](LICENSE)
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
python ./scripts/setup.py install
```
## Usage

### Running with no executable arguments

#### Running the server
```bash
PYTHONPATH=$PYTHONPATH:. ./bin/securedrop_server
```
#### Running the client
```bash
PYTHONPATH=$PYTHONPATH:. ./bin/securedrop
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

## License
[MIT](LICENSE)
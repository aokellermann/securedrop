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
PYTHONPATH=$PYTHONPATH:. ./bin/securedrop_server --port 6789 --file example_file.json --verbose True 
```
#### Running the client
```bash
PYTHONPATH=$PYTHONPATH:. ./bin/securedrop --port 6789 --file example_file.json --verbose True 
```

## Contributing
To read more about the design and security features used in this project see the [contributing file](CONTRIBUTING.MD).

## License
[MIT](LICENSE)
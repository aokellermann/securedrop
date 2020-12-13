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
### Running the server
```bash
PYTHONPATH=$PYTHONPATH:. ./bin/securedrop_server
```
### Running the client
```bash
PYTHONPATH=$PYTHONPATH:. ./bin/securedrop
```

## Contributing
To read more about the design and security features used in this project see the [contributing file](CONTRIBUTING.MD).

## License
[MIT](LICENSE)
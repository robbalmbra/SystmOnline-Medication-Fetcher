# SystmOnline Medication Fetcher

A Python script to interact with the SystmOnline platform, allowing users to log in, query their prescribed medications, and place medication orders.

## Features

- Login authentication for SystmOnline
- Fetch and display prescribed medications
- Option to order medications interactively
- Supports command-line arguments for automation

## Usage

```sh
python medication.py --username YOUR_USERNAME --password YOUR_PASSWORD --medications
```

To order medications:

```sh
python medication.py --username YOUR_USERNAME --password YOUR_PASSWORD --order-medications --all
```

## Requirements

- Python 3.x
- `requests`
- `BeautifulSoup4`
- `pandas`

## Installation

```sh
pip install -r requirements.txt
```

## License

MIT License


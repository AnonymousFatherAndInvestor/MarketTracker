# MarketTracker

A minimal Flask dashboard to track global equities, rates, currencies, commodities and ETF factors.

## Setup

Install dependencies (internet access required):

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python app.py
```

Open `http://localhost:5000` in your browser.

## Deploying to Render

This repository includes configuration files for deployment on
[Render](https://render.com/). The service definition in `render.yaml`
uses the free plan and runs the application with Gunicorn. Simply push
this repository to a connected GitHub account and create a new Web
Service in Render.

Render will automatically install dependencies using
`requirements.txt` and start the server with the command defined in the
`Procfile` or `render.yaml`.

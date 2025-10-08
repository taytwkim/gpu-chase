# GPU Chase 

## Cloud and Machine Learning Assignment 2

In this assignment, we use GCP's Python SDK to launch GPU-provisioned VMs.

* ***Situation***: You are working for a startup, you don’t get GCP premium support, and your company needs 1 GPU to run an urgent AI model.
* ***Mission***: Find a zone and a GPU type that your company can use (any GPU is fine).

## ✅ Deliverables

* Code that iterates through all regions and zones of Google Cloud.
* Code that attempts to create a VM with the selected GPU type.
* A table with at least 10 zones tested, GPU available (Y/N), GPU allocated to VM (Y/N).

## 📁 Output
* `regions.txt`: table of all GCP regions (name, status, and zones per region).
* `zones.txt`: table of all GCP zones (zone, status, parent region).
* `gpu_chase.txt`: table of VM launch attempts (zone, VM type, GPU type, GPU availability [Y/N], GPU allocated [Y/N], success [Y/N], error code).
* `logs.txt`: runtime log with debug messages and detailed errors for troubleshooting.

## 🚀 Setup

1. Set up Python venv
```bash!
python3 -m venv .venv
```

2. Activate venv
```bash!
source .venv/bin/activate
```

3. Upgrade `pip`
```
python3 -m pip install --upgrade pip
```

4. Install dependencies
```bash!
python3 -m pip install -r requirements.txt
```

5. Run code
```bash!
python3 gpu_chase.py > output/logs.txt
```

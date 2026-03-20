# Helena Food Tracker

A web app for tracking baby food introductions by group and week.

Built with Python (Flask) + vanilla JS + SQLite.

---

## Running locally

**Requirements:** Python 3.8+

```bash
git clone https://github.com/nunogilrocha/food-starter-tracker.git
cd food-starter-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install flask
python3 app.py
```

Open http://localhost:5000 in your browser.
The SQLite database (`data.db`) is created automatically on first run.

---

## Deploying on a Raspberry Pi

### 1. Clone and install

SSH into your Pi, then:

```bash
git clone https://github.com/nunogilrocha/food-starter-tracker.git
cd food-starter-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install flask
```

### 2. Verify it runs

```bash
python3 app.py
```

Open `http://<pi-ip>:5000` from another device on the same network to confirm it works. Then stop it with `Ctrl+C`.

### 3. Run as a background service (starts on boot)

Copy the service file and edit it to replace `YOUR_USER` with your Pi username (check with `whoami`):

```bash
sudo cp deploy/food-tracker.service /etc/systemd/system/food-tracker.service
sudo nano /etc/systemd/system/food-tracker.service
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable food-tracker
sudo systemctl start food-tracker
```

Check it's running:

```bash
sudo systemctl status food-tracker
```

### 4. Updating the app

```bash
cd food-starter-tracker
git pull
sudo systemctl restart food-tracker
```

> **Note:** The virtual environment only needs to be created once. After that, the systemd service uses it automatically via the full path to `.venv/bin/python3`.

---

## Running tests

```bash
python3 -m pytest tests/
```

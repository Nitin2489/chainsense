import threading
import time
import requests
import random
import hashlib
import json
import uuid

SERVER_URL = "http://127.0.0.1:8000/submit"
CLIENT_COUNT = 20
SEND_INTERVAL = 2 


def generate_payload():
    return {
        "temperature": random.uniform(20, 40),
        "noise": random.uniform(30, 90),
        "humidity": random.uniform(30, 80)
    }


def sign_payload(payload):
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def client_worker(client_id):
    print(f"Client started: {client_id}")

    while True:
        payload = generate_payload()
        signature = sign_payload(payload)

        data = {
            "client_id": client_id,
            "payload": payload,
            "signature": signature,
            "timestamp": time.time()
        }

        try:
            response = requests.post(SERVER_URL, json=data)
            print(f"{client_id} → {response.status_code}")
        except Exception as e:
            print(f"{client_id} failed:", e)

        time.sleep(SEND_INTERVAL)


if __name__ == "__main__":
    threads = []

    for i in range(CLIENT_COUNT):
        client_id = f"client_{uuid.uuid4().hex[:6]}"
        t = threading.Thread(target=client_worker, args=(client_id,))
        t.daemon = True
        t.start()
        threads.append(t)

    while True:
        time.sleep(1)

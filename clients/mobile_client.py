import requests
import time
import random
import uuid

SERVER_URL = "http://127.0.0.1:8000/submit"

client_id = "client_" + uuid.uuid4().hex[:6]

print("Client started:", client_id)

while True:

    payload = {
        "temperature": random.uniform(20, 40),
        "noise": random.uniform(50, 90)
    }

    data = {
        "client_id": client_id,
        "payload": payload,
        "signature": "dummy_signature",
        "timestamp": time.time()
    }

    try:
        requests.post(SERVER_URL, json=data)
    except:
        pass

    time.sleep(2)

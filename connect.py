import requests

proxies = {
    "http": "http://127.0.0.1:2081",
    "https": "http://127.0.0.1:2081"
}

try:
    r = requests.get("https://api.telegram.org", proxies=proxies, timeout=5)
    print("Status code:", r.status_code)
except Exception as e:
    print("Error:", e)

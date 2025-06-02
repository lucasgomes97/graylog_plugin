import os
import requests
from dotenv import load_dotenv

load_dotenv()

GRAYLOG_URL = os.getenv("GRAYLOG_URL")
USERNAME = os.getenv("GRAYLOG_USER")
PASSWORD = os.getenv("GRAYLOG_PASSWORD")

def get_logs(query="error", range_secs=3600, limit=10):
    url = f"{GRAYLOG_URL}/api/search/universal/relative"
    params = {
        "query": query,
        "range": range_secs,
        "limit": limit
    }
    headers = {"Accept": "application/json"}
    response = requests.get(url, auth=(USERNAME, PASSWORD), headers=headers, params=params)

    if response.status_code != 200:
        raise Exception(f"Erro ao buscar logs: {response.status_code} - {response.text}")

    data = response.json()
    messages = [msg["message"]["full_message"] for msg in data.get("messages", [])]
    return messages

logs = get_logs(query="error", range_secs=3600, limit=10)

logs_unidos = "\n\n".join(logs)

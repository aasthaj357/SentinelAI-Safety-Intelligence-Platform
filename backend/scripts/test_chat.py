import requests

chat_payload = {
    "project_id": "cf22819d-7f92-496c-906b-b5709011f62e",
    "message": "What is the safety risk?",
    "history": []
}
chat_res = requests.post("http://127.0.0.1:8000/api/chat/", json=chat_payload)
print("Chat response:", chat_res.json())

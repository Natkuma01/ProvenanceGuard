import requests

url = "http://localhost:5001/submit"
payload = {
    "text" : "The sun dipped below the horizon, painting the sky in hues of amber and rose. I sat on the porch, coffee in hand, watching the neighborhood slowly go quiet.", 
    "creator_id": "test-user-1"
}

response = requests.post(url, json=payload)
print("Status Code:", response.status_code)
print("Raw Response Text:\n", response.text)
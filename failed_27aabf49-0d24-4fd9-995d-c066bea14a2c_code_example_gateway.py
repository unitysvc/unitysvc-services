import os
import requests

# Environment variables set by UnitySVC after enrollment
base_url = os.environ["SERVICE_BASE_URL"]
api_key = os.environ["UNITYSVC_API_KEY"]
enrollment_code = os.environ["ENROLLMENT_CODE"]
headers = {"Authorization": f"Bearer {api_key}"}

# Submit feedback (tell the engine you liked an item)
feedback = [{"UserId": enrollment_code, "ItemId": "item-1", "FeedbackType": "like"}]
resp = requests.post(f"{base_url}/api/feedback", json=feedback, headers=headers)
print(f"Feedback: {resp.status_code}")

# Get personalized recommendations
resp = requests.get(f"{base_url}/api/recommend/{enrollment_code}?n=5", headers=headers)
print(f"Recommendations: {resp.json()}")
#!/usr/bin/env python3
"""
Create Instagram session from browser cookies
"""

import json
import os

# Your cookies
cookies = {
    "csrftoken": "8TlE9ilMpdnZC0l7i9SyvPz7yV5eEkp4",
    "datr": "F7-NaOembGizfXOaW_YPPeVq",
    "dpr": "1.25",
    "ds_user_id": "34326079012",
    "ig_did": "1748E1E3-2805-45FD-9770-D71297D7340B",
    "ig_nrcb": "1",
    "mid": "aI2_GQALAAHF_UTaWqH6FCEYuPYz",
    "ps_l": "1",
    "ps_n": "1",
    "rur": "RVA\\05434326079012\\0541791448338:01fef83cec4dca0d7b745526cadfb62a606144e0e08b0914a2a87c78b1f76de7ddf5eb78",
    "sessionid": "34326079012%3AHcV41JaJQOyeaH%3A17%3AAYjZjl9QB_xhKVTIviwO9JMHmXpKVZtGYaMQRNsfqQ",
    "wd": "870x730"
}

# Create session file for instagrapi
session_data = {
    "cookies": cookies,
    "user_id": 34326079012,
    "username": "nancygrandeq99"
}

# Save to worker folder
os.makedirs('worker', exist_ok=True)
with open('worker/instagram_session.json', 'w') as f:
    json.dump(session_data, f, indent=2)

print("✅ Session created from browser cookies!")
print("📁 Saved to: worker/instagram_session.json")
print("\n🚀 Now run: python local_instagram_checker.py")

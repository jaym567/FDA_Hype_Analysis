import requests
import json

def check_credits():
    url = "https://api.openalex.org/works?per_page=1"
    headers = {"User-Agent": "mailto:jmodi7@jh.edu"}
    response = requests.get(url, headers=headers)
    
    # OpenAlex doesn't always show credits in the meta for successful requests
    # But it might be in the headers
    credits_used = response.headers.get("X-RateLimit-Credits-Used")
    credits_remaining = response.headers.get("X-RateLimit-Remaining")
    
    print(f"Status Code: {response.status_code}")
    print(f"X-RateLimit-Credits-Used: {credits_used}")
    print(f"X-RateLimit-Remaining: {credits_remaining}")
    
    # If not in headers, we can estimate based on our own tracking
    if not credits_used:
        print("Note: X-RateLimit headers not found in successful response.")

if __name__ == "__main__":
    check_credits()

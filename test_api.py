import http.client
import json

def test_instagram_api():
    try:
        conn = http.client.HTTPSConnection("social-download-all-in-one.p.rapidapi.com")
        
        payload = json.dumps({
            "url": "https://www.instagram.com/reel/DH-oZK7zOS4/?igsh=aW1xMzJ2enkwYXlt"
        })
        
        headers = {
            'x-rapidapi-key': "d51a95d960mshb5f65a8e122bb7fp11b675jsn63ff66cbc6cf",
            'x-rapidapi-host': "social-download-all-in-one.p.rapidapi.com",
            'Content-Type': "application/json"
        }
        
        conn.request("POST", "/v1/social/autolink", payload, headers)
        res = conn.getresponse()
        data = res.read()
        
        print(f"Status Code: {res.status}")
        print(f"Response: {data.decode('utf-8')[:1000]}")
        
        if res.status == 200:
            response_data = json.loads(data.decode('utf-8'))
            if 'medias' in response_data:
                print(f"\nFound {len(response_data['medias'])} media files")
                for i, media in enumerate(response_data['medias']):
                    print(f"Media {i+1}: {media.get('type', 'unknown')} - {media.get('quality', 'unknown')}")
            return True
        else:
            print(f"API Error: {res.status}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_instagram_api()
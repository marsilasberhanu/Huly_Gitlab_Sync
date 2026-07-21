from app.clients.huly_client import HulyClient
import httpx

def test_run():
    print("Initializing Huly Proxy Client...")
    client = HulyClient()
    
    # Replace with your actual Huly project identifier
    project_id = "6a5f3a1ae71459b02a3521f7" 

    try:
        new_issue = client.create_issue(
            project_id=project_id,
            title="Automated Test Issue from FastAPI",
            description="Testing the Docker proxy translation bridge!"
        )
        print("Success! ✅ Issue created.")
        
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error: {e.response.status_code}")
        print(e.response.text)
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    test_run()
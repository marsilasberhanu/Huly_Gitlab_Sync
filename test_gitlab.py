from app.clients.gitlab_client import GitLabClient

def test_run():
    # Initialize our new wrapper
    client = GitLabClient()
    
    # 1. Fetch projects to get a valid Project ID (Optional, but helpful)
    projects = client.list_projects()
    print(f"Found {len(projects)} projects.")
    
    # Replace with a real project ID from the printout above
    PROJECT_ID = 83673383 
    
    # 2. Test creating an issue
    print("Attempting to create an issue...")
    new_issue = client.create_issue(
        project_id=PROJECT_ID, 
        title="Automated Sync Test", 
        description="This issue was created via Python code!"
    )
    
    print(f"Success! Issue created at: {new_issue.get('web_url')}")

if __name__ == "__main__":
    test_run()
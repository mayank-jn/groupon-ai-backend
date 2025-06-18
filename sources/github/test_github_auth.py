import os
from github import Github

if __name__ == "__main__":
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set.")
        exit(1)
    try:
        g = Github(token)
        user = g.get_user()
        print(f"Authenticated as: {user.login}")
        repos = list(user.get_repos())
        print(f"Accessible repositories: {len(repos)} (public + private)")
        print("First 5 repos:")
        for repo in repos[:5]:
            print(f"- {repo.full_name} (private: {repo.private})")
    except Exception as e:
        print(f"GitHub authentication failed: {e}")
        exit(1) 
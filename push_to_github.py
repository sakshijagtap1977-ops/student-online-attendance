"""
push_to_github.py - Utility to push the project to GitHub repository.
Usage:
    python push_to_github.py <YOUR_GITHUB_PERSONAL_ACCESS_TOKEN>
or set GITHUB_TOKEN environment variable:
    $env:GITHUB_TOKEN="your_token_here"
    python push_to_github.py
"""

import sys
import os
from dulwich.repo import Repo
import dulwich.porcelain

REMOTE_REPO = "https://github.com/sakshijagtap1977-ops/attendance.git"

def push_project(token=None):
    if not token:
        token = os.environ.get("GITHUB_TOKEN")

    if not token and len(sys.argv) > 1:
        token = sys.argv[1].strip()

    if not token:
        print("\n" + "="*60)
        print(" [!] GitHub Authentication Required")
        print(" To push code to https://github.com/sakshijagtap1977-ops/attendance.git,")
        print(" GitHub requires a Personal Access Token (Classic with 'repo' scope or Fine-grained).")
        print("\n Run:")
        print("   python push_to_github.py <YOUR_GITHUB_TOKEN>")
        print(" or in PowerShell:")
        print('   $env:GITHUB_TOKEN="ghp_xxxx..."; python push_to_github.py')
        print("="*60 + "\n")
        sys.exit(1)

    # Clean token if prefixed with ghp_ or bearer
    token = token.strip()
    auth_url = f"https://{token}@github.com/sakshijagtap1977-ops/attendance.git"

    repo = Repo('.')
    print(f"[*] Preparing to push local 'main' branch to {REMOTE_REPO}...")

    try:
        dulwich.porcelain.push(repo, auth_url, 'refs/heads/main')
        print("\n" + "="*60)
        print(" [SUCCESS] Project successfully pushed to GitHub!")
        print(" Repository URL: https://github.com/sakshijagtap1977-ops/attendance")
        print("="*60 + "\n")
    except Exception as e:
        print(f"\n[ERROR] Failed to push: {e}")
        print("Please check that your token has 'repo' (write) permissions for sakshijagtap1977-ops/attendance.")
        sys.exit(1)

if __name__ == '__main__':
    push_project()

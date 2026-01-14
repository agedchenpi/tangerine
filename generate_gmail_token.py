#!/usr/bin/env python3
"""
Generate Gmail OAuth2 token using localhost redirect.

This script:
1. Starts a local web server on port 8080
2. Opens browser for Google authorization
3. Captures the callback and exchanges for tokens
4. Saves token.json

Usage:
    python generate_gmail_token.py

Note: Run this on a machine with a browser (not inside Docker).
"""

import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send'
]

def main():
    # Paths - use local paths when running outside Docker
    credentials_path = os.getenv('GMAIL_CREDENTIALS_PATH', 'secrets/credentials.json')
    token_path = os.getenv('GMAIL_TOKEN_PATH', 'secrets/token.json')

    # Check for absolute path (Docker) vs relative path (local)
    if not os.path.isabs(credentials_path):
        # Running locally, use relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        credentials_path = os.path.join(script_dir, credentials_path)
        token_path = os.path.join(script_dir, token_path)

    if not os.path.exists(credentials_path):
        print(f"ERROR: Credentials file not found at {credentials_path}")
        print("\nPlease download OAuth2 credentials from Google Cloud Console")
        print("and save as 'secrets/credentials.json'")
        return 1

    print("\n" + "="*60)
    print("Gmail OAuth2 Authorization")
    print("="*60)
    print(f"\nCredentials: {credentials_path}")
    print(f"Token will be saved to: {token_path}")
    print("\nThis will open a browser window for authorization.")
    print("Make sure you've added http://localhost:8080/ as an")
    print("authorized redirect URI in Google Cloud Console.")
    print("="*60 + "\n")

    try:
        # Create OAuth flow with localhost redirect
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_path,
            scopes=SCOPES
        )

        # Try to run local server - will open browser if available
        # On headless servers, it prints the URL to visit manually
        try:
            creds = flow.run_local_server(
                port=8080,
                prompt='consent',
                success_message='Authorization successful! You can close this window.',
                open_browser=True
            )
        except Exception as browser_error:
            if "browser" in str(browser_error).lower():
                print("\nNo browser available. Starting server manually...")
                print("Visit this URL in your browser:\n")

                # Generate auth URL manually
                auth_url, _ = flow.authorization_url(prompt='consent')
                print(auth_url)
                print("\nAfter authorizing, you'll be redirected to localhost:8080")
                print("The server is waiting to capture the response...")

                # Run server without opening browser
                creds = flow.run_local_server(
                    port=8080,
                    prompt='consent',
                    success_message='Authorization successful! You can close this window.',
                    open_browser=False
                )
            else:
                raise

        # Save token
        token_dir = os.path.dirname(token_path)
        if token_dir and not os.path.exists(token_dir):
            os.makedirs(token_dir, exist_ok=True)

        with open(token_path, 'w') as f:
            f.write(creds.to_json())

        print(f"\nSUCCESS: Token saved to {token_path}")

        # Test the connection
        print("\nTesting Gmail API connection...")
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        print(f"Connected as: {profile.get('emailAddress')}")
        print(f"Total messages: {profile.get('messagesTotal')}")

        print("\nGmail authentication is now configured!")
        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        return 1

if __name__ == '__main__':
    exit(main())

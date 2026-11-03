# Pace

A web app for the North American AI Challenge, built with Flask.

## How to run (Windows PowerShell)

1. Create the virtual environment (first time only):
   ```
   python -m venv venv
   ```
2. Turn it on:
   ```
   venv\Scripts\Activate.ps1
   ```
3. Install the packages (first time only):
   ```
   pip install -r requirements.txt
   ```
4. Start the app:
   ```
   python app.py
   ```
5. Open http://127.0.0.1:5000 in your browser.

API keys go in a `.env` file, which is never committed. It needs:
```
ANTHROPIC_API_KEY=your-key
SECRET_KEY=any-long-random-text
```
(`SECRET_KEY` lets Flask remember each user's theme.)

Optional, for Google Health in Settings > Demo controls (Google Cloud project in testing mode):
```
GOOGLE_CLIENT_ID=your-web-client-id
GOOGLE_CLIENT_SECRET=your-web-client-secret
```
In Google Cloud, add `http://127.0.0.1:5000/google/callback` as an authorized redirect URI
and add each tester's email as a test user.

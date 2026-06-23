# Integration Guide: Google AI & GitHub Webhook Setup

This guide describes how to configure environment credentials and webhooks for the Cortex system, specifically for the Second Brain and Homelab modules.

---

## 1. Google AI (Gemini) API Key

The RAG module utilizes the Google Gemini API (`gemini-embedding-2` and `gemini-3.5-flash`) to generate text embeddings and retrieve context.

### Setup Steps:
1. **Get the Key**:
   - Go to [Google AI Studio](https://aistudio.google.com/).
   - Sign in with your Google account.
   - Click **Get API key** and select/create a project to generate a new key.
2. **Environment Configuration**:
   - Save this key in your environment configuration.
   - The Python runtime reads this from two primary environment variables (with fallback):
     - `GOOGLE_API_KEY`
     - `GEMINI_API_KEY`
   - You can add it to your local environment file at `src/secondbrain/.env.local`:
     ```bash
     GOOGLE_API_KEY=AIzaSy...your_actual_key_here...
     ```

---

## 2. GitHub Webhook Setup for Homelab Sync

To keep the Homelab read-only vector search up-to-date, a GitHub push webhook triggers the synchronization pipeline whenever updates are pushed to your repository.

### Setup Steps:
1. **Expose Cortex Webhook Endpoint**:
   - The webhook payload URL must be reachable by GitHub. If you are developing locally, use a tunnel tool like **Ngrok** or **Cloudflare Tunnel** to expose your server:
     ```bash
     ngrok http 8080
     ```
   - Payload endpoint path: `/api/v1/homelab/webhook` (or the Go endpoint proxying request payload to Second Brain service).
2. **Configure Webhook on GitHub**:
   - Go to your repository on GitHub (e.g., `github.com/dungxbuif/Homelab`).
   - Navigate to **Settings** ➔ **Webhooks** ➔ **Add webhook**.
   - Fill in the configuration:
     - **Payload URL**: `https://<your-public-subdomain>.ngrok-free.app/api/v1/homelab/webhook`
     - **Content type**: Select `application/json`
     - **Secret**: Generate a strong random token. Example:
       ```bash
       openssl rand -hex 32
       ```
     - **Which events**: Select **Just the push event** (specifically on your canonical branches like `main`).
     - **Active**: Ensure the checkbox is checked.
   - Click **Add webhook**.
3. **Environment Setup**:
   - Save the same webhook secret token in your backend configuration:
     ```bash
     GITHUB_WEBHOOK_SECRET=your_generated_secret_here
     ```
   - The webhook verification logic `verify_signature` in [homelab.py](../../src/secondbrain/homelab.py) validates the signature header `X-Hub-Signature-256` to prevent unauthorized sync trigger requests.

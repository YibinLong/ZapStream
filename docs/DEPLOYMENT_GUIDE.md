# ZapStream Deployment Guide (AWS CDK + S3)

This playbook documents the exact sequence we use today to publish the ZapStream stack. It is written for an agentic LLM (e.g. GPT‑5.1 codex) that can run shell commands. The repo already contains the Lambda source (`lambda_fixed/`), CDK app (`/cdk`), and the static Next.js frontend.

---

## 0. Requirements

| Tool | Version/Notes |
| --- | --- |
| Node.js / npm | Uses the project `package-lock.json` (Node 20 works fine). |
| Python 3.11 | Needed only for Lambda packaging handled by CDK. |
| AWS CLI v2 | Must be configured with access to account `971422717446` in `us-west-2`. |
| AWS CDK v2 (CLI) | Already listed in `/cdk/package.json`; we invoke via `npx cdk`. |

**Environment variables (.env):**

- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION=us-west-2`
- `NEXT_PUBLIC_ZAPSTREAM_API_URL=https://9kuup7mcac.execute-api.us-west-2.amazonaws.com/v1`
- `NEXT_PUBLIC_ZAPSTREAM_API_KEY=dev_key_123`
- `NEXT_PUBLIC_APP_URL=http://zapstream-app-1762821749.s3-website-us-west-2.amazonaws.com`

> The `.env` file in the repo already contains working values. Leave them as-is for production builds.

---

## 1. Backend (Lambda + API Gateway + DynamoDB)

The CDK stack packages `lambda_fixed/` and deploys `ZapStreamServerlessStack`.

1. **Install dependencies (once per session)**
   ```bash
   cd /Users/yibin/Documents/WORKZONE/VSCODE/GAUNTLET_AI/5_Week/ZapStream
   npm install
   cd cdk
   npm install
   ```

2. **Deploy the stack**
   ```bash
   cd /Users/yibin/Documents/WORKZONE/VSCODE/GAUNTLET_AI/5_Week/ZapStream/cdk
   npx cdk deploy ZapStreamServerlessStack --require-approval never
   ```

   - The CDK app zips `../lambda_fixed` automatically.
   - Success output reports the API endpoint (currently `https://9kuup7mcac.execute-api.us-west-2.amazonaws.com/v1/`).

3. **Smoke test the API**
   ```bash
   API=https://9kuup7mcac.execute-api.us-west-2.amazonaws.com/v1
   curl -s $API/health
   curl -s -H "Authorization: Bearer dev_key_123" "$API/inbox?limit=5"
   ```

   Both calls should return HTTP 200 JSON responses.

---

## 2. Frontend (Next.js static export)

The production site is served from `s3://zapstream-app-1762821749` in `us-west-2`.

1. **Build the site**
   ```bash
   cd /Users/yibin/Documents/WORKZONE/VSCODE/GAUNTLET_AI/5_Week/ZapStream
   npm run build
   ```
   - Output goes to the `out/` directory (Next.js static export).

2. **Sync to S3**
   ```bash
   aws s3 sync out/ s3://zapstream-app-1762821749 --delete --region us-west-2
   ```
   - The bucket is already configured for static website hosting.

3. **Verify**
   - Visit `http://zapstream-app-1762821749.s3-website-us-west-2.amazonaws.com/`.
   - Ensure the dashboard shows live stats (events, pending, acknowledged) and the Event Stream lists the most recent events without errors.

---

## 3. Troubleshooting

| Problem | Action |
| --- | --- |
| `cdk deploy` fails with missing context | Run `npm install` in `/cdk`, then retry. |
| Lambda errors mentioning syntax | Confirm edits were saved in `lambda_fixed/`, redeploy CDK. |
| Frontend shows stale data | Re-run `npm run build` and `aws s3 sync out/ ... --delete`. Clear browser cache or hard-refresh. |
| API requests blocked by CORS | Backend already sets permissive CORS. Ensure requests use the API Gateway URL, not localhost. |

---

## 4. One-Line Summary

Run `npx cdk deploy ZapStreamServerlessStack --require-approval never`, then `npm run build` and `aws s3 sync out/ s3://zapstream-app-1762821749 --delete --region us-west-2`. Verify the API and S3 site load successfully.

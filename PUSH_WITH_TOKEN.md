# Push to GitHub Using Personal Access Token

GitHub CLI installation requires elevated privileges. Let's use a Personal Access Token instead.

## Step 1: Create Personal Access Token on GitHub

1. Go to: https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Fill in:
   - **Token name:** `pycomby-push`
   - **Expiration:** 90 days (or longer if you prefer)
   - **Scopes:** Check only `repo` (full control of repositories)
4. Click **"Generate token"**
5. **Copy the token** (you won't see it again)
6. Save it somewhere temporary

## Step 2: Push Using the Token

Run this command:

```bash
cd "c:/Users/bardo/OneDrive/Dokumente/GitHub/pycomby"
git push -u origin main
```

When prompted:
- **Username:** `bardo84`
- **Password:** Paste the token (from Step 1)

## Step 3: Save Credentials (Optional)

After first push, Windows Credential Manager will save your credentials automatically, so you won't need the token again.

To verify it was saved:
- Windows → Credential Manager
- Look for `git:https://github.com` entry
- It should show `bardo84` as the username

## After Push

Verify on GitHub: https://github.com/bardo84/pycomby

You should see:
- ✓ 15 files
- ✓ All commits
- ✓ README visible

## Troubleshooting

If the token doesn't work:
1. Go back to https://github.com/settings/tokens
2. Delete the old token
3. Create a new one with the same steps

If you get "credential rejected":
- Clear Windows Credential Manager and try again
- Settings → Credential Manager → Windows Credentials
- Look for git entries and remove them

## Safety

**Important:** 
- Never share your personal access token
- Treat it like a password
- If exposed, delete the token immediately from GitHub settings
- Create a new one if needed

---

Ready? Run the push command above!

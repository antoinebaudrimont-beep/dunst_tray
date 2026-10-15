# Publishing

The maintainer authorized a public GitHub repository named `dunst_tray` under
the authenticated account. This publishes the existing development history as
a pre-release project; it does not imply a stable release or authorize a tag.

## Publication checks

- Start from a clean, inspected working tree and preserve existing commits.
- Keep application code, installed preferences, and private history unchanged.
- Rerun pure tests and the opt-in GTK suite when an X11 session is available.
- Verify README dependency and install instructions against the installer.
- Review all tracked files and the complete diff. Review historical blobs too:
  removing a file or path from the latest commit does not remove earlier copies.
- Never commit databases, local settings, credentials, or personal notifications.
- Git author identities are part of commit history and become public when that
  history is pushed. Resolve any privacy conflict before publication rather
  than rewriting history without authorization.

## Command-line workflow

From the existing checkout, inspect authentication and the destination first:

```sh
gh auth status
git status --short
git remote -v
gh repo view antoinebaudrimont-beep/dunst_tray
```

If the destination does not exist and publication is authorized, create an
empty public repository using the existing checkout:

```sh
gh repo create antoinebaudrimont-beep/dunst_tray \
  --public \
  --description "Lightweight GTK notification center and unread tray bell for Dunst on X11" \
  --source=. --remote=origin
git push -u origin main
```

If it already exists, inspect its contents and history before changing it.
Do not overwrite unrelated content, force-push, or generate a replacement Git
history. Subsequent authorized updates use ordinary commits and normal pushes.

## Verify, then report

```sh
gh repo view antoinebaudrimont-beep/dunst_tray \
  --json url,visibility,defaultBranchRef
git rev-parse HEAD
git ls-remote origin refs/heads/main
gh api repos/antoinebaudrimont-beep/dunst_tray/readme --jq .sha
```

Compare local/remote commit IDs and README blob IDs, confirm source files and
rendered README content, and check public accessibility. Report exact test
results and unverified compatibility checks. If authentication or permissions
block publication, record the exact blocker without claiming a successful push.

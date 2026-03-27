# ARCH-11: GitHub Actions Workflow Commits Directly to Main

## Severity
Low (solo project), Medium (if contributors are added)

## Location
`.github/workflows/build-push.yml` — "Update deployment image tag" step (lines 34–41)

## Description
After a successful build and push, the workflow uses `git commit` + `git push` to update `platform/k8s/deployment.yaml` with the new image SHA and commit it directly to `main`. The workflow has `contents: write` permission to do this.

Current consequences for a solo project: minimal. The ci commit is noisy in the log but harmless.

Future consequences if contributors are added or branch protection is enabled:
- **Merge conflicts**: If a contributor has a branch open that touches `deployment.yaml` (unlikely) or if two pushes to main happen in quick succession, the second push's image tag update will conflict with the first commit.
- **Branch protection bypass**: If branch protection is added to require PRs for `main` (standard practice), this workflow will break — it pushes directly and cannot open a PR. The fix at that point requires special configuration (allow the `github-actions` bot to bypass branch protection), which is a security exception.
- **Audit confusion**: The deployment SHA is embedded in a commit that was not code-reviewed. In any audit trail, it's unclear whether the `deployment.yaml` change was intentional or automated.

## Remediation

**Pattern: GitOps with a separate config repo or a dedicated deploy branch**

Option 1 (simplest): Keep the commit, but push to a `deploy` branch instead of `main`. A simple GitOps watcher (Flux, Argo, or a webhook) syncs the deploy branch to the cluster. `main` stays human-only.

Option 2 (correct for multi-contributor): Use the image SHA tag in the workflow output and apply it directly to the cluster via `kubectl set image` or `kubectl rollout restart` without writing it back to the repo. The source of truth for what's deployed is the cluster, not a committed YAML. The `deployment.yaml` in the repo becomes the *desired* state template, not the live state.

Option 3 (current + minimal change): Add a `[skip ci]` marker to the bot commit message so the image update doesn't trigger another workflow run. Does not fix the branch protection problem but prevents accidental CI loops.

## Related
None — standalone architectural concern

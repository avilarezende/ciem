#!/usr/bin/env bash
# Publica branches de trabalho no GitHub (avilarezende/ciem) e abre PRs se gh estiver autenticado.
set -euo pipefail

REPO_HTTPS="${GITHUB_REPO_URL:-https://github.com/avilarezende/ciem.git}"
REMOTE="${GITHUB_REMOTE:-github}"
BASE="${BASE_BRANCH:-main}"

BRANCHES=(
  "cursor/fix-gitleaks-tests-a834"
  "cursor/owasp-hardening-a834"
)

if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
  git remote add "$REMOTE" "$REPO_HTTPS"
fi

if [[ -n "${GH_TOKEN:-${GITHUB_TOKEN:-}}" ]]; then
  TOKEN="${GH_TOKEN:-$GITHUB_TOKEN}"
  git remote set-url "$REMOTE" "https://x-access-token:${TOKEN}@github.com/avilarezende/ciem.git"
  echo "Usando token GH_TOKEN/GITHUB_TOKEN para push."
elif command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  gh auth setup-git
  echo "Usando autenticação gh."
else
  echo "ERRO: defina GH_TOKEN (PAT com repo+workflow) ou rode: gh auth login" >&2
  exit 1
fi

git fetch "$REMOTE" "$BASE"

for branch in "${BRANCHES[@]}"; do
  if git show-ref --verify --quiet "refs/heads/$branch" || git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
    echo "=== Push $branch ==="
    git push -u "$REMOTE" "refs/heads/$branch:refs/heads/$branch" \
      || git push -u "$REMOTE" "refs/remotes/origin/$branch:refs/heads/$branch"
    if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
      if ! gh pr view "$branch" --repo avilarezende/ciem >/dev/null 2>&1; then
        title=$(git log -1 --format=%s "origin/$branch" 2>/dev/null || git log -1 --format=%s "$branch")
        gh pr create --repo avilarezende/ciem --base "$BASE" --head "$branch" \
          --title "$title" --body "Sincronizado automaticamente a partir do Origin." || true
      else
        echo "PR já existe para $branch"
      fi
    fi
  else
    echo "Branch local/origin ausente: $branch (ignorada)"
  fi
done

echo "Pronto. Actions: https://github.com/avilarezende/ciem/actions"

#!/usr/bin/env bash
# Sincroniza o projeto CIEM com Origin (Cursor) e GitHub.
set -euo pipefail

REPO="rodrigo-rezende/ciem"
ORIGIN_URL="https://origin.cursor.com/git/${REPO}.git"
GITHUB_URL="https://github.com/${REPO}.git"

echo "==> CIEM — Sincronização de repositórios"
echo "    Origin: ${ORIGIN_URL}"
echo "    GitHub: ${GITHUB_URL}"

if ! origin repo view "${REPO}" &>/dev/null; then
  echo "==> Criando repositório no Origin..."
  origin repo create ciem --repo "${REPO}" --default-branch main
fi

if ! git remote get-url origin &>/dev/null; then
  git remote add origin "${ORIGIN_URL}"
else
  git remote set-url origin "${ORIGIN_URL}"
fi

echo "==> Enviando para Origin..."
git push -u origin main

if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  if ! gh repo view "${REPO}" &>/dev/null; then
    echo "==> Criando repositório no GitHub..."
    gh repo create "${REPO}" --public --source=. --remote=github --push
  else
    git remote add github "${GITHUB_URL}" 2>/dev/null || git remote set-url github "${GITHUB_URL}"
    git push -u github main
  fi
else
  echo "==> Espelhando GitHub via Origin..."
  origin repo create-mirrored "${REPO}" || true
fi

echo "==> Sincronização concluída."

#!/usr/bin/env bash
# Sincroniza o projeto CIEM com Origin (Cursor) e GitHub.
set -euo pipefail

REPO="avilarezende/ciem"
ORIGIN_URL="https://origin.cursor.com/git/${REPO}.git"
GITHUB_URL="https://github.com/${REPO}.git"

echo "==> CIEM — Sincronização de repositórios"
echo "    Origin: ${ORIGIN_URL}"
echo "    GitHub: ${GITHUB_URL}"

# Criar repositório no Origin (se não existir)
if ! origin repo view "${REPO}" &>/dev/null; then
  echo "==> Criando repositório no Origin..."
  origin repo create ciem --repo "${REPO}" --default-branch main
fi

# Configurar remote
if ! git remote get-url origin &>/dev/null; then
  git remote add origin "${ORIGIN_URL}"
else
  CURRENT=$(git remote get-url origin)
  if [[ "$CURRENT" != *"${REPO}"* ]]; then
    echo "==> Atualizando remote origin para ${REPO}..."
    git remote set-url origin "${ORIGIN_URL}"
  fi
fi

echo "==> Enviando para Origin..."
git push -u origin HEAD:main

# GitHub via gh CLI ou espelhamento Origin
if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
  if ! gh repo view "${REPO}" &>/dev/null 2>&1; then
    echo "==> Criando repositório no GitHub..."
    gh repo create "${REPO}" --public --description "CIEM — Centro Integrado de Estatística e Manutenção (ZTNA)" --source=. --remote=github --push
  else
    git remote add github "${GITHUB_URL}" 2>/dev/null || git remote set-url github "${GITHUB_URL}"
    git push -u github HEAD:main
  fi
else
  echo "==> Espelhando GitHub via Origin..."
  origin repo create-mirrored "${REPO}" 2>/dev/null || echo "    (espelhamento já existe ou requer autenticação)"
fi

echo "==> Sincronização concluída."
echo "    GitHub: ${GITHUB_URL}"
echo "    Origin: ${ORIGIN_URL}"

# Publica o repositório no GitHub (avilarezende/conversador-pop-se)
# Pré-requisito: gh autenticado (gh auth login)

$ErrorActionPreference = "Stop"
$gh = "C:\Program Files\GitHub CLI\gh.exe"

if (-not (Test-Path $gh)) {
    Write-Error "GitHub CLI não encontrado. Instale com: winget install GitHub.cli"
}

& $gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Execute primeiro: gh auth login -h github.com -p https -w"
    exit 1
}

$desc = "Chatbot modular PoP-SE/RNP para clientes de conectividade em Sergipe. RAG, Docker, CI/CD."
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Cria repositório (ignora se já existir)
& $gh repo view avilarezende/conversador-pop-se 2>$null
if ($LASTEXITCODE -ne 0) {
    & $gh repo create conversador-pop-se `
        --public `
        --description $desc `
        --source . `
        --remote origin `
        --push
} else {
  git push -u origin main
}

& $gh repo edit avilarezende/conversador-pop-se `
    --description $desc `
    --add-topic chatbot --add-topic pop-se --add-topic rnp `
    --add-topic docker --add-topic fastapi --add-topic rag `
    --add-topic zabbix --add-topic ci-cd

Write-Host "Repositório publicado: https://github.com/avilarezende/conversador-pop-se"

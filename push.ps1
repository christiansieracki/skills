# Erster Push oder spaetere Aenderungen.
# Voraussetzung: git ist installiert und bei GitHub angemeldet.
# Wer lieber klickt, nimmt GitHub Desktop: Ordner hinzufuegen, Publish.

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$remote = "https://github.com/christiansieracki/skills.git"

if (-not (Test-Path ".git")) {
    Write-Host "Neues Repository anlegen..."
    git init
    git branch -M main
    git remote add origin $remote
    Write-Host ""
    Write-Host "Das Repository muss auf github.com schon existieren."
    Write-Host "Falls nicht: dort anlegen unter dem Namen 'skills', ohne README,"
    Write-Host "ohne .gitignore und ohne Lizenz, dann dieses Skript nochmal starten."
    Write-Host ""
}

git add -A

$nachricht = Read-Host "Commit-Nachricht (Enter fuer 'Skills aktualisiert')"
if ([string]::IsNullOrWhiteSpace($nachricht)) { $nachricht = "Skills aktualisiert" }

git commit -m $nachricht
git push -u origin main

Write-Host ""
Write-Host "Fertig. In Claude holst du die Aenderung mit:"
Write-Host "  /plugin marketplace update"
Write-Host "  /plugin update volleyball@christiansieracki-skills"

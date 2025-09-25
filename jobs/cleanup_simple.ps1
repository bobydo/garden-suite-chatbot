# Simple Qdrant Cleanup Script
Write-Host "=== Qdrant Cleanup ===" -ForegroundColor Cyan
Write-Host ""

# Check if user wants to continue
$confirm = Read-Host "Delete ALL Qdrant collections? (y/N)"
if ($confirm -ne 'y' -and $confirm -ne 'Y') {
    Write-Host "Cancelled." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit
}

Write-Host "Deleting collections..." -ForegroundColor Yellow

# Delete guides_index
try {
    Invoke-RestMethod -Uri "http://localhost:6333/collections/guides_index" -Method Delete | Out-Null
    Write-Host "✓ Deleted guides_index" -ForegroundColor Green
} catch {
    Write-Host "! guides_index may not exist" -ForegroundColor Yellow
}

# Delete pdf_index  
try {
    Invoke-RestMethod -Uri "http://localhost:6333/collections/pdf_index" -Method Delete | Out-Null
    Write-Host "✓ Deleted pdf_index" -ForegroundColor Green
} catch {
    Write-Host "! pdf_index may not exist" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Cleanup complete!" -ForegroundColor Green
Write-Host "You can now run: python manage.py ingest_websites" -ForegroundColor Cyan
Read-Host "Press Enter to exit"
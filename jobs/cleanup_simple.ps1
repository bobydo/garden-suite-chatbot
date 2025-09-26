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

# Delete website_index
try {
    Invoke-RestMethod -Uri "http://localhost:6333/collections/website_index" -Method Delete | Out-Null
    Write-Host "✓ Deleted website_index" -ForegroundColor Green
} catch {
    Write-Host "! website_index may not exist" -ForegroundColor Yellow
}

# Delete excel_index
try {
    Invoke-RestMethod -Uri "http://localhost:6333/collections/excel_index" -Method Delete | Out-Null
    Write-Host "✓ Deleted excel_index" -ForegroundColor Green
} catch {
    Write-Host "! excel_index may not exist" -ForegroundColor Yellow
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
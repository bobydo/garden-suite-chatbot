# Qdrant Cleanup Script
# This script clears all collections from Qdrant to start fresh
# Run this when you need to reset all vector data

Write-Host "=== Qdrant Cleanup Script ===" -ForegroundColor Cyan
Write-Host "This will delete ALL collections and data from Qdrant!" -ForegroundColor Yellow
Write-Host ""

# Check if Qdrant is running
try {
    $response = Invoke-RestMethod -Uri "http://localhost:6333/collections" -Method Get -TimeoutSec 5
    Write-Host "✓ Qdrant is running on localhost:6333" -ForegroundColor Green
} catch {
    Write-Host "✗ Qdrant is not running on localhost:6333" -ForegroundColor Red
    Write-Host "Please start Qdrant first using: C:\Tools\Qdrant\start-qdrant.bat" -ForegroundColor Yellow
    exit 1
}

# Confirm deletion
$confirmation = Read-Host "Are you sure you want to delete ALL collections? (y/N)"
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Host "Operation cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Deleting collections..." -ForegroundColor Yellow

# List of collections to delete
$collections = @("website_index", "pdf_index", "excel_index")

foreach ($collection in $collections) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:6333/collections/$collection" -Method Delete
        if ($response.result -eq $true) {
            Write-Host "✓ Deleted collection: $collection" -ForegroundColor Green
        } else {
            Write-Host "! Collection $collection may not exist (this is normal)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "! Collection $collection may not exist (this is normal)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=== Cleanup Complete! ===" -ForegroundColor Green
Write-Host "You can now run fresh ingestion commands:" -ForegroundColor Cyan
Write-Host "  python manage.py ingest_websites" -ForegroundColor White
Write-Host "  python manage.py ingest_pdfs" -ForegroundColor White
Write-Host "  python manage.py ingest_texts" -ForegroundColor White
Write-Host ""

# Verify cleanup
Write-Host "Verifying cleanup..." -ForegroundColor Cyan
try {
    $collections_after = Invoke-RestMethod -Uri "http://localhost:6333/collections" -Method Get
    if ($collections_after.result.collections.Count -eq 0) {
        Write-Host "✓ All collections successfully deleted!" -ForegroundColor Green
    } else {
        Write-Host "Remaining collections:" -ForegroundColor Yellow
        $collections_after.result.collections | ForEach-Object { 
            Write-Host "  - $($_.name)" -ForegroundColor White
        }
    }
} catch {
    Write-Host "Could not verify cleanup status" -ForegroundColor Yellow
}

Write-Host ""
Read-Host "Press Enter to close"
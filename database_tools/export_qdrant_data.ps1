# Export all Qdrant collections to timestamped JSON files
# Author: Generated for Garden Suite Chatbot
# Usage: .\export_qdrant_data.ps1

param(
    [string]$QdrantUrl = "http://localhost:6333"
)

# Generate timestamp for filenames
$timestamp = Get-Date -Format "yyyyMMdd"

# Define collections and output files
$collections = @("website_index", "pdf_index")
$outputFiles = @(
    "qdrant_website_index_all_points_$timestamp.json",
    "qdrant_pdf_index_all_points_$timestamp.json"
)

Write-Host "=== QDRANT DATA EXPORT ===" -ForegroundColor Cyan
Write-Host "Timestamp: $timestamp" -ForegroundColor Gray
Write-Host "Qdrant URL: $QdrantUrl" -ForegroundColor Gray
Write-Host ""

# Check if files exist and delete them
for ($i = 0; $i -lt $outputFiles.Count; $i++) {
    $file = $outputFiles[$i]
    if (Test-Path $file) {
        Write-Host "Deleting existing file: $file" -ForegroundColor Yellow
        Remove-Item $file -Force
    }
}

# Export each collection
for ($i = 0; $i -lt $collections.Count; $i++) {
    $collection = $collections[$i]
    $outputFile = $outputFiles[$i]
    
    Write-Host "Exporting collection: $collection" -ForegroundColor Yellow
    
    try {
        # Check if collection exists
        $collectionInfo = Invoke-RestMethod -Uri "$QdrantUrl/collections/$collection" -Method Get
        Write-Host "   Collection info - Vectors: $($collectionInfo.result.vectors_count), Status: $($collectionInfo.result.status)" -ForegroundColor Green
        
        # Fetch all points with pagination
        $allPoints = @()
        $offset = $null
        $batchCount = 0
        
        do {
            $body = @{
                limit = 100
                with_payload = $true
                with_vector = $false
            }
            if ($offset) {
                $body.offset = $offset
            }
            
            $response = Invoke-RestMethod -Uri "$QdrantUrl/collections/$collection/points/scroll" -Method Post -Headers @{"Content-Type"="application/json"} -Body ($body | ConvertTo-Json)
            
            $allPoints += $response.result.points
            $offset = $response.result.next_page_offset
            $batchCount++
            
            Write-Host "   Batch $batchCount - Retrieved $($allPoints.Count) points so far..." -ForegroundColor Green
            
        } while ($offset)
        
        # Save to JSON file
        $allPoints | ConvertTo-Json -Depth 10 | Out-File -FilePath $outputFile -Encoding UTF8
        
        Write-Host "   SUCCESS: Saved $($allPoints.Count) points to $outputFile" -ForegroundColor Cyan
        
    } catch {
        Write-Host "   ERROR exporting $collection : $($_.Exception.Message)" -ForegroundColor Red
        continue
    }
    
    Write-Host ""
}

# Create summary report
$summaryFile = "qdrant_export_summary_$timestamp.txt"
if (Test-Path $summaryFile) {
    Remove-Item $summaryFile -Force
}

$summary = @()
$summary += "=== QDRANT EXPORT SUMMARY ==="
$summary += "Generated: $(Get-Date)"
$summary += "Export Date: $timestamp"
$summary += ""

$totalPoints = 0
for ($i = 0; $i -lt $collections.Count; $i++) {
    $collection = $collections[$i]
    $outputFile = $outputFiles[$i]
    
    if (Test-Path $outputFile) {
        try {
            $data = Get-Content $outputFile | ConvertFrom-Json
            $pointCount = $data.Count
            $totalPoints += $pointCount
            
            $summary += "$collection : $pointCount points -> $outputFile"
            
            # Add sample entries
            if ($pointCount -gt 0) {
                $summary += "  Sample entries:"
                for ($j = 0; $j -lt [Math]::Min(3, $pointCount); $j++) {
                    $point = $data[$j]
                    if ($collection -eq "website_index") {
                        $summary += "    $($j+1). URL: $($point.payload.metadata.url)"
                        $summary += "       Content: $($point.payload.page_content.Substring(0, [Math]::Min(100, $point.payload.page_content.Length)))..."
                    } else {
                        $summary += "    $($j+1). Source: $($point.payload.metadata.source)"
                        $summary += "       Page: $($point.payload.metadata.page), Content: $($point.payload.page_content.Substring(0, [Math]::Min(100, $point.payload.page_content.Length)))..."
                    }
                }
                $summary += ""
            }
        } catch {
            $summary += "$collection : ERROR reading exported file"
        }
    } else {
        $summary += "$collection : EXPORT FAILED - file not found"
    }
}

$summary += "TOTAL POINTS: $totalPoints"
$summary += ""
$summary += "Files created:"
foreach ($file in $outputFiles) {
    if (Test-Path $file) {
        $size = [math]::Round((Get-Item $file).Length / 1MB, 2)
        $summary += "  $file ($size MB)"
    }
}

$summary | Out-File -FilePath $summaryFile -Encoding UTF8

Write-Host "Export Summary:" -ForegroundColor Cyan
Write-Host "   Total Points: $totalPoints" -ForegroundColor Green
Write-Host "   Summary saved to: $summaryFile" -ForegroundColor Green
Write-Host ""
Write-Host "Export completed successfully!" -ForegroundColor Green
#!/usr/bin/env pwsh
# KINOBOT Railway Deployment Script

$projectId = "a54919e9-76b5-4d7e-b3b7-2e8c414061dc"
$envVars = @{
    "BOT_TOKEN" = "8736516835:AAF_jLaDsPS1PmPwCEGHNRrgTorgd1dLWoU"
    "BOT_USERNAME" = "kinobot_uz"
    "SUPER_ADMIN_IDS" = "8555328454"
    "BASE_CHANNEL_ID" = "-1001234567890"
    "LOG_CHANNEL_ID" = "-1001234567890"
    "COMMENT_GROUP_ID" = "-1001234567890"
    "FORCE_SUBSCRIPTION" = "true"
    "MAINTENANCE_MODE" = "false"
    "LOG_LEVEL" = "INFO"
}

Write-Host "🚀 KINOBOT Railway Deployment Script" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# Step 1: Git Push
Write-Host "`n📤 Pushing to GitHub..." -ForegroundColor Yellow
cd C:\Users\komilov\Desktop\KINOBOT
git add .
git commit -m "Update deployment config" 2>$null
git push origin main

Write-Host "✓ GitHub push complete" -ForegroundColor Green

# Step 2: Environment variables output for manual Railway setup
Write-Host "`n🔧 Railway Environment Variables to Add:" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Yellow

$envVars.GetEnumerator() | ForEach-Object {
    Write-Host "$($_.Key)=$($_.Value)" -ForegroundColor Cyan
}

Write-Host "`n📝 Instructions:" -ForegroundColor Yellow
Write-Host "1. Open: https://railway.com/project/$projectId" -ForegroundColor White
Write-Host "2. Go to Bot Service → Settings → Variables" -ForegroundColor White
Write-Host "3. Add these variables (copy above)" -ForegroundColor White
Write-Host "4. Click Deploy button" -ForegroundColor White
Write-Host "5. Check Logs for 'Starting polling...'" -ForegroundColor White

Write-Host "`n✅ All files pushed to GitHub!" -ForegroundColor Green
Write-Host "📱 Bot ready for Railway deployment!" -ForegroundColor Green

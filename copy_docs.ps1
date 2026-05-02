# Copy documentation into the portable package.
Copy-Item "说明文档.md" -Destination "dist\secondhandsql\" -Force
Copy-Item "要求.md" -Destination "dist\secondhandsql\" -Force
Copy-Item "计划.md" -Destination "dist\secondhandsql\" -Force
Copy-Item "run.bat" -Destination "dist\secondhandsql\" -Force
Write-Host "Documentation copied to dist\secondhandsql\"

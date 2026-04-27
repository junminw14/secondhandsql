# 复制文档到 dist 目录
Copy-Item "说明文档.md" -Destination "dist\secondhandsql\" -Force
Copy-Item "要求.md" -Destination "dist\secondhandsql\" -Force
Copy-Item "计划.md" -Destination "dist\secondhandsql\" -Force
Copy-Item "防火墙配置说明.md" -Destination "dist\secondhandsql\" -Force
Copy-Item "run.bat" -Destination "dist\secondhandsql\" -Force
Write-Host "文档已复制到 dist\secondhandsql\"
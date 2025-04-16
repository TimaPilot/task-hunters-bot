@echo off
cd /d C:\Users\Admin\Desktop\task-hunters-bot
git pull origin main
git add .
git commit -m "🔁 Автооновлення"
git push origin main
pause

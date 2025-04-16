@echo off
cd /d "D:\Discord TH\task-hunters-bot\bot"
git pull origin main
git add .
git commit -m "Reboot"
git push origin main

@echo off
cd /d C:\Users\Admin\Desktop\task-hunters-bot
echo 📁 Увійшов у директорію task-hunters-bot

echo 📦 Додаємо всі зміни...
git add .

echo 📝 Комітимо...
git commit -m "🔁 Автооновлення"

echo 🚀 Відправляємо у GitHub...
git push origin main

echo ✅ Готово! Зміни надіслані, Railway сам оновить бота.
pause

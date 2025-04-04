# Task Hunters Discord Bot

🎯 **Task Hunters** — це Discord-бот для прийому та виконання замовлень у грі Ukraine GTA 5. Працює на Railway + PostgreSQL.

---

## 🚀 Як вносити зміни в бота

### 1. Зміни код у файлах
Наприклад, у `bot/main.py`, `db_logger.py`, `views.py` тощо.

### 2. Збережи зміни (Ctrl + S)

---

### 3. Відкрий термінал у корені проєкту

```bash
cd путь_до_проекту
```

---

### 4. Закоміть і запуш у GitHub

```bash
git add .
git commit -m "твоє повідомлення про зміни"
git push
```

> 🔁 **GitHub оновлюється — Railway запускає нову версію бота автоматично.**

---

### 5. Перевір статус на Railway

1. Перейди у [Railway.app](https://railway.app)
2. Вибери свій проєкт
3. У вкладці `Deployments` має бути:
```
✅ Build successful
✅ Running main.py
✅ Logged in as Task Hunters Bot#XXXX
```

---

### 6. Тестуй у Discord

- Введи команду `!start`
- Натисни кнопки
- Перевір `!моїзамовлення`
- Якщо щось не працює — подивись `Logs` у Railway

---

## 🛠 Корисні команди Git

```bash
git status       # переглянути зміни
git add .        # додати все
git commit -m "" # створити коміт
git push         # відправити на GitHub
```

---

## 💾 База даних

Використовується Railway PostgreSQL.
- Після створення замовлення — запис у таблицю `orders`
- Збережено: замовник, деталі, виконавець, статус, час

---

## 📁 Структура

```
task-hunters-bot/
├── bot/
│   ├── main.py
│   ├── db_logger.py
├── .env
├── requirements.txt
└── README.md
```

---

✅ Успішного розвитку проєкту, мисливцю 💼
# 💰 Where Is My Money Going (WIMM)

AI-powered personal finance analytics that automatically categorizes your bank transactions and provides meaningful insights into your spending habits.

---

## 📖 Overview

**Where Is My Money Going (WIMM)** is a full-stack personal finance analytics application that helps users understand and manage their spending with ease.

Simply upload your bank statement (CSV, Excel, or PDF), and WIMM automatically classifies every transaction using AI, generates insightful spending analytics, detects recurring subscriptions, and provides personalized financial summaries through an interactive dashboard.

---

## ✨ Features

* 📤 Upload bank statements (CSV, Excel & PDF)
* 🏦 Support for 41+ bank formats
* 💱 Multi-currency transaction support
* 🤖 AI-powered transaction classification
* 📊 Interactive analytics dashboard
* 📈 Spending trends & financial insights
* 💰 Smart budget recommendations
* 🔄 Subscription detection
* 🧾 Transaction management (CRUD)
* 🔐 JWT-based authentication
* 📱 Responsive UI with Dark & Light Mode

---

## 🛠 Tech Stack

### Frontend

* Next.js 14
* React 18
* TypeScript
* Tailwind CSS
* Recharts

### Backend

* Python 3.11
* FastAPI
* SQLAlchemy
* Pydantic

### Database

* PostgreSQL
* SQLite (Development)

### AI / Machine Learning

* Hugging Face Transformers
* DistilBART-MNLI
* Ollama (Optional)

### Deployment

* Docker
* Docker Compose
* Nginx
* Amazon EC2

---

## 📁 Project Structure

```text
WhereIsMyMoney/
├── backend/
├── frontend/
├── Investigations/
├── docker-compose.yml
├── nginx.conf
├── deploy-ec2.sh
├── .env.example
└── README.md
```

---

## 🚀 Getting Started

### Clone the Repository

```bash
git clone https://github.com/ishitachamoli/WhereIsMyMoney.git
```

### Run with Docker

```bash
docker compose up -d --build
```

### Local Development

**Backend**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

---

## 📡 API Documentation

Once the backend is running, Swagger UI is available at:

```text
http://localhost:8000/docs
```

---

## 🔮 Future Improvements

* OCR support for scanned bank statements
* Mobile application
* Predictive expense analysis
* Investment tracking
* Export reports to PDF & Excel
* Multi-language support

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome.

If you'd like to contribute:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push your branch
5. Open a Pull Request

---

## 👩‍💻 Author

**Ishita Chamoli**

GitHub: https://github.com/ishitachamoli

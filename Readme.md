# Tax Activity Backend

Backend service for parsing and managing PEB (Export Declaration) documents.

---

## 🚀 Features

* Upload single & bulk PDF
* Extract structured tax data from PEB documents
* MongoDB integration
* REST API built with FastAPI
* Clean & structured parsing logic

---

## 📦 Project Structure

```
app/
├── routers/
├── services/
├── utils/
├── db/
uploads/        # Folder untuk menyimpan file PDF upload
.env            # Environment variables (tidak di-commit)
.env.example    # Contoh environment
main.py
```

---

## ⚙️ Setup

```bash
docker compose up -d
```

---

## 🔐 Environment Variables

Buat file `.env` di root project, lalu isi seperti berikut:

```env
APP_NAME="ArdiarTax Backend"
DATABASE_URL=postgresql://ardiartax:bukankaumdajal666@db:5432/ardiartax_db
SECRET_KEY=yoursecretkey
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
TESSERACT_PATH=/usr/bin/tesseract
UPLOAD_DIR=uploads/documents
CACHE_DIR=uploads/cache_pdf

```

---

## 📁 Uploads Folder

Pastikan folder `uploads/` sudah tersedia di root project:

```bash
mkdir uploads
```

Folder ini digunakan untuk menyimpan file PDF yang di-upload sebelum diproses.

> ⚠️ Folder `uploads/` tidak akan ikut ter-upload ke Git karena sudah di-ignore di `.gitignore`.

---

## 🧪 API Endpoints

### 🔹 URL Docs API

```
http:://localhost:3031/docs
```

---

## 📝 Notes

* File `.env` bersifat rahasia dan tidak boleh di-commit
* Gunakan `.env.example` sebagai referensi konfigurasi
* Pastikan MongoDB sudah berjalan sebelum menjalankan aplikasi

---

## 📌 Tech Stack

* FastAPI
* MongoDB
* pdfplumber

---

## 👨‍💻 Author

MbadoxDev45
Rio Teguh Ardiara

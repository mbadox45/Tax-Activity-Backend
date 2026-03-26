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
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

---

## 🔐 Environment Variables

Buat file `.env` di root project, lalu isi seperti berikut:

```env
MONGO_URI=mongodb://localhost:27017
DB_NAME=tax_activity
UPLOAD_DIR=uploads
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

### 🔹 Upload Single File

```
POST /upload
```

### 🔹 Upload Multiple Files (Bulk)

```
POST /parse-peb-bulk
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

Tax Activity Backend

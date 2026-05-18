module.exports = {
  apps: [
    {
      name: "tax-activity-backend",
      // Tunjuk langsung ke binary uvicorn di dalam venv Anda
      script: "/home/ict-production/Documents/tax/Tax-Activity-Backend/venv/bin/uvicorn",
      // Masukkan argumen aplikasi di sini
      args: "app.main:app --host 0.0.0.0 --port 8000 --workers 4",
      // Paksa PM2 untuk mengeksekusinya sebagai script biasa (bukan fork python global)
      exec_mode: "fork",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        PYTHONPATH: "."
      }
    }
  ]
};
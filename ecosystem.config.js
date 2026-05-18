module.exports = {
  apps: [
    {
      name: "tax-activity-backend",
      // Gunakan modul uvicorn langsung melalui interpreter venv
      script: "-m uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 3032 --workers 4",
      // Arahkan interpreter ke python bawaan venv Anda secara absolut
      interpreter: "/home/ict-production/Documents/tax/Tax-Activity-Backend/venv/bin/python3",
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
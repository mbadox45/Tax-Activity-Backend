module.exports = {
  apps: [
    {
      name: "tax-activity-backend",
      script: "./venv/bin/uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 8000 --workers 4",
      interpreter: "python3",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        NODE_ENV: "development",
        PYTHONPATH: "."
      },
      env_production: {
        NODE_ENV: "production",
        PYTHONPATH: "."
      },
      output: "./logs/pm2_out.log",
      error: "./logs/pm2_err.log",
      merge_logs: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z"
    }
  ]
};
module.exports = {
  apps : [{
    name: "ardirtax-backend",
    script: "venv/bin/uvicorn",
    args: "app.main:app --host 0.0.0.0 --port 3032",
    interpreter: "none", // Karena kita panggil langsung dari path venv
    env: {
      NODE_ENV: "production",
    },
    autorestart: true,
    watch: false,
    max_memory_restart: '1G'
  }]
}
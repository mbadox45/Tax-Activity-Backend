module.exports = {
  apps: [
    {
      name: "tax-activity-backend",
      script: "./start.sh",
      // Beritahu PM2 bahwa ini adalah file script/binary biasa, bukan aplikasi Node.js
      interpreter: "none", 
      exec_mode: "fork",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "1G"
    }
  ]
};
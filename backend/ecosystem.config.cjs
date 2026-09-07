module.exports = {
  apps: [
    {
      name: "atlas-backend",
      script: "venv/bin/python",
      args: "-m uvicorn server:app --host 0.0.0.0 --port 8000",
      cwd: "./"
    },
    {
      name: "atlas-bot",
      script: "venv/bin/python",
      args: "../telegram_bot.py",
      cwd: "./"
    }
  ]
};

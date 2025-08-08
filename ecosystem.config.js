module.exports = {
    apps: [
      {
        name: 'healzy-b',
        cwd: '/var/www/healzy.app/backend',
        interpreter: '/var/www/healzy.app/backend/venv/bin/python',
        script: '/var/www/healzy.app/backend/manage.py',
        args: 'runserver 127.0.0.1:8000 --noreload',
        instances: 1,
        autorestart: true,
        watch: false,
        max_memory_restart: '1G',
        env: {
          NODE_ENV: 'production',
          DJANGO_SETTINGS_MODULE: 'vrachiapp_backend.settings',
          PYTHONUNBUFFERED: '1',
          PYTHONDONTWRITEBYTECODE: '1',
          PYTHONPATH: '/var/www/healzy.app/backend'
        },
        error_file: '/var/log/pm2/healzy-backend-error.log',
        out_file: '/var/log/pm2/healzy-backend-out.log',
        log_file: '/var/log/pm2/healzy-backend.log',
        time: true,
        kill_timeout: 5000
      }
    ]
  };
  
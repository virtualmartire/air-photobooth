from app import app, update_displayed_photo
from threading import Thread
from gunicorn.app.base import BaseApplication
import os

class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {
            key: value 
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

def main():

    # Get port from environment variable (Heroku sets this)
    port = int(os.environ.get("PORT", 5001))
    
    # Start the photo update thread
    thread = Thread(target=update_displayed_photo, daemon=True)
    thread.start()
    
    # Configure and start Gunicorn
    options = {
        "bind": f"0.0.0.0:{port}",  # Use dynamic port
        "workers": 3,
        "timeout": 120,
        "keepalive": 5,
        "access-logfile": "-",
        "error-logfile": "-"
    }

    StandaloneApplication(app, options).run()

if __name__ == "__main__":
    main()

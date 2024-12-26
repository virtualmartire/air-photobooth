from app import app, update_displayed_photo
from threading import Thread
from gunicorn.app.base import BaseApplication

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
    # Start the photo update thread
    thread = Thread(target=update_displayed_photo, daemon=True)
    thread.start()

    # Configure and start Gunicorn
    options = {
        "bind": "0.0.0.0:5001",  # Listen on all network interfaces
        "workers": 3,
        "timeout": 120,
        # Add these options for better network handling
        "keepalive": 5,
        "access-logfile": "-",  # Log to stdout
        "error-logfile": "-"    # Log to stdout
    }

    StandaloneApplication(app, options).run()

if __name__ == "__main__":
    main()

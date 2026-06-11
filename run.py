from app import create_app
from flask import redirect, url_for
import os

app = create_app(os.getenv('FLASK_ENV', 'development'))

@app.route('/')
def index():
    """Redirect root to login page"""
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    # Localhost only - for local development
    app.run(host='127.0.0.1', port=5000, debug=True)
    
    # Uncomment below to enable network access (other computers on same network)
    # app.run(host='0.0.0.0', port=5000, debug=False)

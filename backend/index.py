from app.factory import create_app
from flask import jsonify

# Create the Flask app instance
app = create_app()

# Add a root route to prevent 404 on the main URL
@app.route('/')
def index():
    return jsonify({
        "status": "success",
        "message": "AI Assignment Generator Backend is running!",
        "version": "2.0.0"
    })

# Vercel looks for 'app' or 'application' or 'handler'
application = app

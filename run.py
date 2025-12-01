from app import create_app

app = create_app()

if __name__ == '__main__':
    # Reverted to standard HTTP for stability.
    # GPS features will work when deployed to a real server (Render/Heroku).
    app.run(host='0.0.0.0', port=5000, debug=True)

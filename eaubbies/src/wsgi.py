from app import app

if __name__ == "__main__":
    app.debug = True
    app.host = "0.0.0.0"
    app.run()

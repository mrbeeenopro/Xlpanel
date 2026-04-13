from app import create_app


app, run_options = create_app()


if __name__ == "__main__":
    app.run(**run_options)

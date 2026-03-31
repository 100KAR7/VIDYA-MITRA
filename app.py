from backend.app import create_app
from backend.runtime import RuntimeSettings

app = create_app()


def _startup_message(settings: RuntimeSettings) -> None:
    local_host = "127.0.0.1" if settings.host == "0.0.0.0" else settings.host
    mode = "debug" if settings.debug else "production"
    print(f"Vidya Mitra is running in {mode} mode at http://{local_host}:{settings.port}", flush=True)
    if settings.host == "0.0.0.0":
        print(f"Listening on all interfaces via {settings.host}:{settings.port}", flush=True)


if __name__ == "__main__":
    settings = RuntimeSettings.from_env()
    try:
        from waitress import serve
    except ImportError:
        serve = None

    _startup_message(settings)

    if settings.debug or serve is None:
        app.run(host=settings.host, port=settings.port, debug=settings.debug)
    else:
        serve(app, host=settings.host, port=settings.port, threads=settings.waitress_threads)
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Vidya-Mitra Running 🚀"
CMD ["sh", "-c", "waitress-serve --host=0.0.0.0 --port=$PORT app:app"]
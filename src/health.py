import threading

from flask import Flask, Response, jsonify

app = Flask(__name__)


@app.get("/healthz")
def healthz() -> tuple[Response, int]:
    return jsonify(status="ok"), 200


@app.get("/readyz")
def readyz() -> tuple[Response, int]:
    return jsonify(status="ready"), 200


@app.get("/livez")
def livez() -> tuple[Response, int]:
    return jsonify(status="alive"), 200


def _run(host: str = "0.0.0.0", port: int = 8080) -> None:
    # Built-in server is fine for a tiny health endpoint
    app.run(host=host, port=port, debug=False, use_reloader=False)


def start_health_server(host: str = "0.0.0.0", port: int = 8080) -> threading.Thread:
    """Start the Flask health server in a daemon thread."""
    t = threading.Thread(target=_run, kwargs={"host": host, "port": port}, daemon=True)
    t.start()
    return t

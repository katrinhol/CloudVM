from flask import Flask, request, jsonify
import logging

from cloud_storage import init_db, save_cloud_data, get_all_cloud_data

app = Flask(__name__)

init_db()


@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_json(force=True)

    logging.info("Cloud received data: %s", data)

    save_cloud_data(data)

    return jsonify({"status": "ok"}), 200


@app.route("/data", methods=["GET"])
def data():
    return jsonify(get_all_cloud_data())


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running"})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=5000)
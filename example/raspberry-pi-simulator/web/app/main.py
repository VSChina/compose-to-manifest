import random
import datetime
from flask import Flask
from flask import render_template
from flask import jsonify
from pymongo import MongoClient

app = Flask(__name__)

@app.route("/latest")
def latest():
    date = datetime.datetime.now()
    t = random.randint(24, 27)
    record = {"datetime": str(date), "temperature": t}
    j = jsonify(record)
    client = MongoClient("mongo:27017")
    Room = client["iot"]["Room"]
    Room.insert(record)
    return j


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=80)

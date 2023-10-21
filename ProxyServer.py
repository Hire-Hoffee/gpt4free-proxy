from flask import Flask, request
import g4f

app = Flask(__name__)


@app.route("/data", methods=["POST"])
async def hello_world():
    try:
        data = request.json

        response = await g4f.ChatCompletion.create_async(
            model="gpt-3.5-turbo",
            messages=data.get("messages"),
        )

        return response
    except Exception as e:
        print(e)
        return "Some error occurred :("


app.run(port=8989, host="0.0.0.0")

from flask import Flask, request, jsonify
import json

app = Flask(__name__) # type: ignore

# File to store pending submissions
PENDING_SUBMISSIONS_FILE = "pending_submissions.json"

@app.route("/submit-bar", methods=["POST"])
def submit_bar():
    data = request.json

    # Load existing submissions
    try:
        with open(PENDING_SUBMISSIONS_FILE, "r") as file:
            submissions = json.load(file)
    except FileNotFoundError:
        submissions = []

    # Add the new submission
    submissions.append(data)

    # Save the updated submissions
    with open(PENDING_SUBMISSIONS_FILE, "w") as file:
        json.dump(submissions, file, indent=4)

    return jsonify({"message": "Submission received!"}), 200 # type: ignore

if __name__ == "__main__":
    app.run(debug=True)
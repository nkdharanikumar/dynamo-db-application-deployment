from flask import Flask, request, jsonify
import boto3

app = Flask(__name__)

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("customers")

@app.route("/customer", methods=["POST"])
def create_customer():
    data = request.json

    table.put_item(
        Item=data
    )

    return jsonify({
        "message": "Customer created",
        "customer": data
    })

@app.route("/customer/<customer_id>", methods=["GET"])
def get_customer(customer_id):

    response = table.get_item(
        Key={"customer_id": customer_id}
    )

    item = response.get("Item")

    if not item:
        return jsonify({"error": "Customer not found"}), 404

    return jsonify(item)

@app.route("/customer/<customer_id>", methods=["PUT"])
def update_customer(customer_id):

    data = request.json

    table.update_item(
        Key={"customer_id": customer_id},
        UpdateExpression="SET #n=:n, email=:e, city=:c",
        ExpressionAttributeNames={
            "#n": "name"
        },
        ExpressionAttributeValues={
            ":n": data["name"],
            ":e": data["email"],
            ":c": data["city"]
        }
    )

    return jsonify({
        "message": "Customer updated"
    })

@app.route("/health")
def health():
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

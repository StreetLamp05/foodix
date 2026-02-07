from flask import Blueprint, jsonify

from ..services.prediction_service import get_all_predictions, get_single_prediction

predictions_bp = Blueprint("predictions", __name__)


@predictions_bp.route("/api/restaurants/<int:restaurant_id>/predictions")
def all_predictions(restaurant_id):
    result = get_all_predictions(restaurant_id)
    return jsonify(result)


@predictions_bp.route(
    "/api/restaurants/<int:restaurant_id>/predictions/<int:ingredient_id>"
)
def single_prediction(restaurant_id, ingredient_id):
    result = get_single_prediction(restaurant_id, ingredient_id)
    if not result:
        return jsonify({"error": "No prediction found for this ingredient"}), 404
    return jsonify(result)

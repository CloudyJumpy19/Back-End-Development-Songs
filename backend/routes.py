from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service is None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"

print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# Implement /health endpoint
######################################################################
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "OK"})

######################################################################
# Implement /count endpoint
######################################################################
@app.route("/count", methods=["GET"])
def count():
    try:
        song_count = db.songs.count_documents({})
        return jsonify({"count": song_count})
    except Exception as e:
        app.logger.error(f"Error counting documents: {str(e)}")
        return jsonify({"error": "Failed to count documents"}), 500

######################################################################
# Implement /song endpoint
######################################################################
@app.route("/song", methods=["GET"])
def songs():
    """Retrieve all songs from the database."""
    try:
        songs_cursor = db.songs.find({})
        songs_list = parse_json(list(songs_cursor))
        return jsonify({"songs": songs_list}), 200
    except Exception as e:
        app.logger.error(f"Error retrieving songs: {str(e)}")
        return jsonify({"error": "Failed to retrieve songs"}), 500

######################################################################
# Implement /song/id endpoint
######################################################################
@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    """Retrieve a song by its ID."""
    try:
        song = db.songs.find_one({"id": id})
        if song is None:
            return jsonify({"message": "song with id not found"}), 404
        return jsonify(song), 200
    except Exception as e:
        app.logger.error(f"Error retrieving song by ID: {str(e)}")
        return jsonify({"error": "Failed to retrieve song by ID"}), 500

######################################################################
# Implement POST /song endpoint
######################################################################
@app.route("/song", methods=["POST"])
def create_song():
    """Create a new song in the database."""
    try:
        # Extract the song data from the request body
        song_data = request.get_json()

        # Check if a song with the same ID already exists
        existing_song = db.songs.find_one({"id": song_data["id"]})
        if existing_song:
            return jsonify({"Message": f"song with id {song_data['id']} already present"}), 302

        # Insert the new song into the database
        result = db.songs.insert_one(song_data)
        return jsonify({"inserted id": str(result.inserted_id)}), 201
    except Exception as e:
        app.logger.error(f"Error creating song: {str(e)}")
        return jsonify({"error": "Failed to create song"}), 500

######################################################################
# Implement DELETE /song/id endpoint
######################################################################
@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    """Delete a song by its ID."""
    try:
        # Try to delete the song with the specified ID
        result = db.songs.delete_one({"id": id})

        if result.deleted_count == 0:
            # If no song was deleted (i.e., the song was not found)
            return jsonify({"message": "song not found"}), 404
        
        # If the song was successfully deleted
        return '', 204  # No content, successful deletion
    except Exception as e:
        app.logger.error(f"Error deleting song: {str(e)}")
        return jsonify({"error": "Failed to delete song"}), 500

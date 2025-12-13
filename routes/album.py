from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from models.mongo import albums_collection
from config import UPLOAD_FOLDER
import os
import uuid

albums_bp = Blueprint('albums', __name__)

# ==============================
# GET ALL ALBUMS WITH PHOTOS
# ==============================
@albums_bp.route('/api/albums', methods=['GET'])
def get_albums():
    albums = list(albums_collection.find())

    for album in albums:
        album["_id"] = str(album["_id"])
        album["photos"] = album.get("photos", [])
        # Ensure all photo URLs are complete
        for photo in album["photos"]:
            if photo.get("url"):
                # If URL doesn't start with http, prepend the base URL
                if not photo["url"].startswith("http"):
                    if photo["url"].startswith("/"):
                        photo["url"] = f"http://localhost:5000{photo['url']}"
                    else:
                        photo["url"] = f"http://localhost:5000/uploads/{photo['url']}"

    return jsonify(albums)

# ==============================
# CREATE ALBUM
# ==============================
@albums_bp.route('/api/albums', methods=['POST'])
def create_album():
    data = request.json
    name = data.get("name")

    if not name:
        return jsonify({"error": "Album name required"}), 400

    if albums_collection.find_one({"name": name}):
        return jsonify({"error": "Album already exists"}), 400

    albums_collection.insert_one({
        "name": name,
        "photos": []
    })

    return jsonify({"message": "Album created successfully"})

# ==============================
# DELETE ALBUM
# ==============================
@albums_bp.route('/api/albums/<album_name>', methods=['DELETE'])
def delete_album(album_name):
    album = albums_collection.find_one({"name": album_name})
    if not album:
        return jsonify({"error": "Album not found"}), 404

    for photo in album.get("photos", []):
        path = os.path.join(UPLOAD_FOLDER, photo["filename"])
        if os.path.exists(path):
            os.remove(path)

    albums_collection.delete_one({"name": album_name})
    return jsonify({"message": "Album deleted successfully"})

# ==============================
# UPLOAD PHOTOS TO ALBUM
# ==============================
@albums_bp.route('/api/albums/<album_name>/photos', methods=['POST'])
def upload_photos(album_name):
    album = albums_collection.find_one({"name": album_name})
    if not album:
        return jsonify({"error": "Album not found"}), 404
    # Support two modes:
    # 1) Admin uploads: request.files['photos'] (multipart/form-data)
    # 2) Associate already-uploaded files: JSON body { photos: [{ filename, url, ... }, ...] }

    photo_list = []

    # JSON association mode
    if request.is_json and request.json.get('photos'):
        incoming = request.json.get('photos')
        if not isinstance(incoming, list):
            return jsonify({"error": "Invalid photos payload"}), 400

        for p in incoming:
            if not isinstance(p, dict):
                continue
            # minimal validation: must have filename
            filename = p.get('filename')
            url = p.get('url') or f"http://localhost:5000/uploads/{filename}"
            if not filename:
                continue
            photo_list.append({
                "filename": filename,
                "url": url
            })

    else:
        # multipart upload mode (existing behavior)
        if 'photos' not in request.files:
            return jsonify({"error": "No photos uploaded"}), 400

        uploaded_photos = request.files.getlist('photos')

        for file in uploaded_photos:
            if not file or not file.filename:
                continue

            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[-1].lower()

            if ext not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                continue

            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(file_path)

            photo_list.append({
                "filename": unique_filename,
                "url": f"http://localhost:5000/uploads/{unique_filename}"
            })

    if not photo_list:
        return jsonify({"error": "No valid photos provided"}), 400

    albums_collection.update_one(
        {"name": album_name},
        {"$push": {"photos": {"$each": photo_list}}}
    )

    return jsonify({
        "message": "Photos added to album successfully",
        "photos": photo_list
    })

# ==============================
# DELETE PHOTO FROM ALBUM
# ==============================
@albums_bp.route('/api/albums/<album_name>/photos/<int:index>', methods=['DELETE'])
def delete_photo(album_name, index):
    album = albums_collection.find_one({"name": album_name})

    if not album or index >= len(album.get("photos", [])):
        return jsonify({"error": "Photo not found"}), 404

    photo = album["photos"][index]
    path = os.path.join(UPLOAD_FOLDER, photo["filename"])

    if os.path.exists(path):
        os.remove(path)

    album["photos"].pop(index)
    albums_collection.update_one(
        {"name": album_name},
        {"$set": {"photos": album["photos"]}}
    )

    return jsonify({"message": "Photo deleted successfully"})

# ==============================
# SERVE UPLOADED FILES
# ==============================
@albums_bp.route('/uploads/<filename>')
def serve_photo(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

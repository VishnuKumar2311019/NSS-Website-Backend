from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from models.mongo import albums_collection
from config import UPLOAD_FOLDER
import os

albums_bp = Blueprint('albums', __name__)

# Get albums and photos
@albums_bp.route('/api/albums', methods=['GET'])
def get_albums():
    albums = list(albums_collection.find({}, {"_id": 0}))
    album_map = {album["name"]: album.get("photos", []) for album in albums}
    return jsonify({"albums": list(album_map.keys()), "photos": album_map})

# Create album
@albums_bp.route('/api/albums', methods=['POST'])
def create_album():
    data = request.json
    name = data.get("name")
    if albums_collection.find_one({"name": name}):
        return jsonify({"error": "Album already exists"}), 400
    albums_collection.insert_one({"name": name, "photos": []})
    return jsonify({"message": "Album created"})

# Delete album
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
    return jsonify({"message": "Album deleted"})

# Upload photo
@albums_bp.route('/api/albums/<album_name>/photos', methods=['POST'])
def upload_photos(album_name):
    album = albums_collection.find_one({"name": album_name})
    if not album:
        return jsonify({"error": "Album not found"}), 404
    
    if 'photos' not in request.files:
        return jsonify({"error": "No photos uploaded"}), 400

   
    uploaded_photos = request.files.getlist('photos') or request.files.getlist('photo')
    if not uploaded_photos:
        return jsonify({"error": "No photos uploaded"}), 400

    photo_list = []
    for file in uploaded_photos:
        if not file or not file.filename:
            continue
            
        # Basic security validation
        filename = secure_filename(file.filename)
        if not filename:
            continue
            
        # Check file extension
        if not ('.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}):
            continue
            
        # Generate unique filename to prevent conflicts
        import uuid
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # Ensure the file is saved within the upload directory
        if not os.path.abspath(file_path).startswith(os.path.abspath(UPLOAD_FOLDER)):
            continue
            
        file.save(file_path)
        photo_url = f"http://localhost:5000/uploads/{unique_filename}"
        photo_list.append({"name": unique_filename, "url": photo_url, "filename": unique_filename})
    
    albums_collection.update_one(
        {"name": album_name},
        {"$push": {"photos": {"$each": photo_list}}}
    )

    return jsonify({"message": "Photos uploaded","uploadedPhotos": photo_list})

# Delete photo
@albums_bp.route('/api/albums/<album_name>/photos/<int:index>', methods=['DELETE'])
def delete_photo(album_name, index):
    album = albums_collection.find_one({"name": album_name})
    if not album or "photos" not in album or index >= len(album["photos"]):
        return jsonify({"error": "Photo not found"}), 404
    
    photo = album["photos"][index]
    path = os.path.join(UPLOAD_FOLDER, photo["filename"])
    if os.path.exists(path):
        os.remove(path)

    album["photos"].pop(index)
    albums_collection.update_one({"name": album_name}, {"$set": {"photos": album["photos"]}})
    return jsonify({"message": "Photo deleted"})

# Serve uploaded photos
@albums_bp.route('/uploads/<filename>')
def serve_photo(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# Serve assets photos
@albums_bp.route('/assets/<path:filepath>')
def serve_asset(filepath):
    assets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets')
    print(f"DEBUG: Serving asset from {assets_path}, filepath: {filepath}")
    print(f"DEBUG: Full path: {os.path.join(assets_path, filepath)}")
    print(f"DEBUG: File exists: {os.path.exists(os.path.join(assets_path, filepath))}")
    return send_from_directory(assets_path, filepath)

def access_request_document(user_id, file_id):
    return {
        "user_id": user_id,
        "file_id": file_id,
        "status": "pending"
    }

def success_response(data=None, message="Success", code=200):
    return {
        "code": code,
        "status": True,
        "message": message,
        "data": data
    }


def error_response(message="Error", code=400):
    return {
        "code": code,
        "status": False,
        "message": message,
        "data": None
    }
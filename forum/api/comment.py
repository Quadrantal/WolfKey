from forum.services.comment_services import (
    create_comment_service,
    edit_comment_service,
    delete_comment_service,
    get_comments_service,
)

def create_comment_api(request, solution_id, data):
    return create_comment_service(request, solution_id, data)

def edit_comment_api(request, comment_id, data):
    return edit_comment_service(request, comment_id, data)

def delete_comment_api(request, comment_id):
    return delete_comment_service(request, comment_id)

def get_comments_api(request, solution_id):
    return get_comments_service(request, solution_id)
import secrets
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from app.config import settings

def identity(request, reviewer=False):
    token=request.headers.get('Authorization','').removeprefix('Bearer ')
    is_reviewer=secrets.compare_digest(token,settings.reviewer_token)
    is_analyst=secrets.compare_digest(token,settings.analyst_token)
    if not is_reviewer and not is_analyst:raise NotAuthorizedException('Valid local demo token required')
    if reviewer and not is_reviewer:raise PermissionDeniedException('Reviewer role required')
    return 'reviewer-local' if is_reviewer else 'analyst-local'

from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.openapi import OpenAPIConfig
from app.api.routes import routes
from app.models import migrate
from app.api.journey import routes as journey_routes
from app.api.voice import routes as voice_routes
from app.config import settings

def _get_cors_origins() -> list[str]:
    raw = settings.cors_origins.strip()
    if raw == '*' or not raw:
        return ['*']
    return [o.strip() for o in raw.split(',') if o.strip()]

cors_config = CORSConfig(
    allow_origins=_get_cors_origins(),
    allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['Authorization', 'Content-Type', 'Accept', 'Origin', 'X-Requested-With'],
)

app = Litestar(
    route_handlers=routes + journey_routes + voice_routes,
    on_startup=[migrate],
    cors_config=cors_config,
    openapi_config=OpenAPIConfig(title='Synthetic MSME Underwriting Desk', version='0.3.0'),
    request_max_body_size=11 * 1024 * 1024,
    debug=False,
)

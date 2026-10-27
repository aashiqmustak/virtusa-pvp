from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.openapi import OpenAPIConfig
from app.api.routes import routes
from app.models import migrate
from app.api.journey import routes as journey_routes
from app.api.voice import routes as voice_routes
app=Litestar(route_handlers=routes+journey_routes+voice_routes,on_startup=[migrate],cors_config=CORSConfig(allow_origins=['http://localhost:5173','http://localhost:8080'],allow_methods=['GET','POST'],allow_headers=['Authorization','Content-Type']),openapi_config=OpenAPIConfig(title='Synthetic MSME Underwriting Desk',version='0.3.0'),request_max_body_size=11*1024*1024,debug=False)

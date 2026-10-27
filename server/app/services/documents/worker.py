"""PDF decoder isolation with a wall-clock deadline enforced by parent."""
import sys,json
try:
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(1536*1024*1024,1536*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(75,75))
except ImportError:pass # Windows: parent subprocess deadline still applies.
from app.services.documents.parser import parse
if __name__=='__main__':
    try:print(json.dumps(parse(sys.argv[1])))
    except Exception as exc:print(str(exc),file=sys.stderr);sys.exit(1)

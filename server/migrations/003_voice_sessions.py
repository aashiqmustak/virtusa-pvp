"""Add voice session records without changing existing application columns."""
from app.models import migrate
if __name__=='__main__':migrate()

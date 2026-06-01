from datetime import datetime, timedelta, timezone

from app.libs.extensions import db
from app.models.base import Base

CHINA_TZ = timezone(timedelta(hours=8))


class ClassroomEvent(Base):
    """
    课堂事件模型类
    """
    __tablename__ = 'classroom_event'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False)
    source = db.Column(db.String(50), nullable=False, default='system')
    concept_type = db.Column(db.String(50))
    name = db.Column(db.String(255))
    content = db.Column(db.Text)
    event_payload = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        created_at = self.created_at
        if created_at:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            created_at = created_at.astimezone(CHINA_TZ)

        return {
            'id': self.id,
            'session_id': self.session_id,
            'event_type': self.event_type,
            'source': self.source,
            'concept_type': self.concept_type,
            'name': self.name,
            'content': self.content,
            'payload': self.event_payload or {},
            'created_at': created_at.isoformat() if created_at else None,
        }

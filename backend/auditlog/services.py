from .models import AuditEvent


def record_event(actor, action, target, summary, details=None):
    """Write a small, append-only application audit event for an important change."""
    meta = getattr(target, '_meta', None)
    return AuditEvent.objects.create(
        actor=actor if getattr(actor, 'is_authenticated', False) else None,
        action=action,
        object_type=meta.label if meta else type(target).__name__,
        object_id=str(getattr(target, 'pk', '') or ''),
        summary=summary,
        details=details or {},
    )

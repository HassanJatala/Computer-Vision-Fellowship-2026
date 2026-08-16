from database.db import get_connection


def save_event(event, object_class="person", confidence=None, source_id="camera_1"):
    conn = get_connection()
    duration = (event.resolved_time - event.detected_time) if event.resolved_time else None
    conn.execute("""
        INSERT OR REPLACE INTO events
        (event_id, event_type, severity, track_id, object_class, zone_id,
         start_time, end_time, duration, status, confidence, evidence_path, evidence_crop_path, source_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event.event_id, event.event_type, event.severity, event.track_id, object_class,
        event.zone_id, event.detected_time, event.resolved_time, duration, event.status,
        confidence, event.evidence_path, event.evidence_crop_path, source_id
    ))
    conn.commit()
    conn.close()


def get_events(event_type=None, severity=None, zone_id=None, status=None):
    conn = get_connection()
    query = "SELECT * FROM events WHERE 1=1"
    params = []
    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    if zone_id:
        query += " AND zone_id = ?"
        params.append(zone_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_event_status(event_id, status):
    conn = get_connection()
    conn.execute("UPDATE events SET status = ? WHERE event_id = ?", (status, event_id))
    conn.commit()
    conn.close()
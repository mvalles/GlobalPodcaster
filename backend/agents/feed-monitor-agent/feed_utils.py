"""
Funciones genéricas y utilidades para el agente Feed Monitor MCP.
Contiene helpers reutilizables para operaciones con Firestore y feeds RSS.
"""
import feedparser
import hashlib
from firebase_admin import firestore

def serialize(obj):
    """
    Convierte objetos de fecha Firestore (DatetimeWithNanoseconds) y otros no serializables a string.
    """
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    if type(obj).__name__ == 'DatetimeWithNanoseconds':
        return str(obj)
    return obj

def get_feed_id(feed_url: str) -> str:
    """
    Genera un identificador único para un feed RSS a partir de su URL usando SHA256.
    """
    return hashlib.sha256(feed_url.encode('utf-8')).hexdigest()

def check_feed_for_new_episodes(db, feed_url: str) -> list:
    """
    Devuelve una lista de episodios nuevos (no procesados) de un feed RSS.
    Filtra los episodios que ya están en la subcolección processed_episodes de Firestore.
    """
    feed_id = get_feed_id(feed_url)
    feed_doc = db.collection("feeds").document(feed_id)
    processed_ref = feed_doc.collection("processed_episodes")
    processed_guids = set(doc.id for doc in processed_ref.stream())
    try:
        feed = feedparser.parse(feed_url)
        if feed.bozo:
            return []
        entries = []
        for entry in feed.entries:
            # El GUID puede estar en 'guid', 'id', o 'link'. Preferimos 'guid', luego 'id', luego 'link'.
            guid = entry.get('guid') or entry.get('id') or entry.get('link')
            if not guid:
                continue
            ep = dict(entry)
            ep['guid'] = guid
            entries.append(ep)
        new_episodes = [
            {**ep, 'feed_url': feed_url, 'feed_id': feed_id}
            for ep in entries if ep['guid'] not in processed_guids
        ]
        return new_episodes
    except Exception as e:
        print(f"Error en check_feed_for_new_episodes: {e}")
        return []
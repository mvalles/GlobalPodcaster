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

def get_user_feeds(db, user_id: str):
    """
    Obtiene los feeds de un usuario desde Firestore, incluyendo información personalizada.
    No serializa fechas (ver función extendida más abajo).
    """
    feeds = []
    user_ref = db.collection("users").document(user_id)
    feeds_ref = user_ref.collection("feeds")
    for feed_doc in feeds_ref.stream():
        feed_data = feed_doc.to_dict()
        feed_id = feed_doc.id
        global_feed_ref = db.collection("feeds").document(feed_id)
        global_feed = global_feed_ref.get()
        feed_url = global_feed.to_dict().get("feed_url", "") if global_feed.exists else ""
        feeds.append({
            "feed_id": feed_id,
            "feed_url": feed_url,
            "custom_name": feed_data.get("custom_name", ""),
            "active": feed_data.get("active", True),
            "added_at": feed_data.get("added_at", None),
        })
    return feeds

def get_all_feeds(db):
    """
    Obtiene todos los feeds globales desde Firestore, sin serializar fechas.
    """
    feeds = []
    feeds_ref = db.collection("feeds")
    for feed_doc in feeds_ref.stream():
        feed_data = feed_doc.to_dict()
        feed_id = feed_doc.id
        feed_obj = {
            "feed_id": feed_id,
            "feed_url": feed_data.get("feed_url", ""),
            "created_at": feed_data.get("created_at", None),
            "metadata": feed_data.get("metadata", {}),
        }
        feeds.append(feed_obj)
    return feeds

def add_feed_to_user(db, user_id: str, feed_url: str, custom_name: str = "", active: bool = True):
    """
    Añade un feed RSS a la lista de un usuario y lo registra globalmente si es nuevo.
    """
    feed_id = get_feed_id(feed_url)
    user_feed_ref = db.collection("users").document(user_id).collection("feeds").document(feed_id)
    feed_ref = db.collection("feeds").document(feed_id)
    user_feed_ref.set({
        "active": active,
        "added_at": firestore.SERVER_TIMESTAMP,
        "custom_name": custom_name
    }, merge=True)
    if not feed_ref.get().exists:
        feed_data = feedparser.parse(feed_url)
        metadata = dict(feed_data.feed)
        feed_ref.set({
            "feed_url": feed_url,
            "metadata": metadata,
            "created_at": firestore.SERVER_TIMESTAMP
        }, merge=True)
    return {"status": "success", "feed_id": feed_id}

def delete_feed_from_user(db, user_id: str, feed_url: str, logger=None):
    """
    Elimina un feed RSS de la lista de un usuario y lo borra globalmente si no lo usa nadie más.
    """
    feed_id = get_feed_id(feed_url)
    user_feed_ref = db.collection("users").document(user_id).collection("feeds").document(feed_id)
    feed_ref = db.collection("feeds").document(feed_id)
    try:
        user_feed_ref.delete()
        if logger:
            logger.info(f"Feed {feed_id} eliminado del usuario {user_id}")
        users_ref = db.collection("users")
        users = users_ref.stream()
        feed_still_used = False
        for user in users:
            uid = user.id
            other_feed_ref = users_ref.document(uid).collection("feeds").document(feed_id)
            if other_feed_ref.get().exists:
                feed_still_used = True
                break
        if not feed_still_used:
            feed_ref.delete()
            if logger:
                logger.info(f"Feed {feed_id} eliminado de la colección global feeds")
        return {"status": "success", "feed_id": feed_id, "feed_global_deleted": not feed_still_used}
    except Exception as e:
        if logger:
            logger.error(f"Error eliminando feed {feed_id} de usuario {user_id}: {e}")
        return {"status": "error", "error": str(e)}

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
def get_user_feeds(db, user_id: str):
    """
    Devuelve los feeds de un usuario con información personalizada desde Firestore.
    Serializa los campos de fecha para evitar errores de JSON.
    """
    feeds = []
    user_ref = db.collection("users").document(user_id)
    feeds_ref = user_ref.collection("feeds")
    for feed_doc in feeds_ref.stream():
        feed_data = feed_doc.to_dict()
        feed_id = feed_doc.id
        global_feed_ref = db.collection("feeds").document(feed_id)
        global_feed = global_feed_ref.get()
        feed_url = global_feed.to_dict().get("feed_url", "") if global_feed.exists else ""
        feed_obj = {
            "feed_id": feed_id,
            "feed_url": feed_url,
            "custom_name": feed_data.get("custom_name", ""),
            "active": feed_data.get("active", True),
            "added_at": feed_data.get("added_at", None),
        }
        # Serializar campos de fecha
        for k, v in feed_obj.items():
            if type(v).__name__ == 'DatetimeWithNanoseconds' or hasattr(v, 'isoformat'):
                feed_obj[k] = serialize(v)
        feeds.append(feed_obj)
    return feeds

def get_all_feeds(db):
    """
    Devuelve todos los feeds globales registrados en la colección feeds de Firestore.
    Serializa los campos de fecha para evitar errores de JSON.
    """
    feeds = []
    feeds_ref = db.collection("feeds")
    for feed_doc in feeds_ref.stream():
        feed_data = feed_doc.to_dict()
        feed_id = feed_doc.id
        feed_obj = {
            "feed_id": feed_id,
            "feed_url": feed_data.get("feed_url", ""),
            "created_at": feed_data.get("created_at", None),
            "metadata": feed_data.get("metadata", {}),
        }
        # Serializar campos de fecha
        for k, v in feed_obj.items():
            if type(v).__name__ == 'DatetimeWithNanoseconds' or hasattr(v, 'isoformat'):
                feed_obj[k] = serialize(v)
        feeds.append(feed_obj)
    return feeds

def add_feed_to_user(db, user_id: str, feed_url: str, custom_name: str = "", active: bool = True):
    """
    Añade un feed RSS a la lista de un usuario y lo registra globalmente si es nuevo.
    """
    feed_id = get_feed_id(feed_url)
    user_feed_ref = db.collection("users").document(user_id).collection("feeds").document(feed_id)
    feed_ref = db.collection("feeds").document(feed_id)
    user_feed_ref.set({
        "active": active,
        "added_at": firestore.SERVER_TIMESTAMP,
        "custom_name": custom_name
    }, merge=True)
    if not feed_ref.get().exists:
        feed_data = feedparser.parse(feed_url)
        metadata = dict(feed_data.feed)
        feed_ref.set({
            "feed_url": feed_url,
            "metadata": metadata,
            "created_at": firestore.SERVER_TIMESTAMP
        }, merge=True)
    return {"status": "success", "feed_id": feed_id}

def delete_feed_from_user(db, user_id: str, feed_url: str, logger=None):
    """
    Elimina un feed RSS de la lista de un usuario y lo borra globalmente si no lo usa nadie más.
    """
    feed_id = get_feed_id(feed_url)
    user_feed_ref = db.collection("users").document(user_id).collection("feeds").document(feed_id)
    feed_ref = db.collection("feeds").document(feed_id)
    try:
        user_feed_ref.delete()
        if logger:
            logger.info(f"Feed {feed_id} eliminado del usuario {user_id}")
        users_ref = db.collection("users")
        users = users_ref.stream()
        feed_still_used = False
        for user in users:
            uid = user.id
            other_feed_ref = users_ref.document(uid).collection("feeds").document(feed_id)
            if other_feed_ref.get().exists:
                feed_still_used = True
                break
        if not feed_still_used:
            feed_ref.delete()
            if logger:
                logger.info(f"Feed {feed_id} eliminado de la colección global feeds")
        return {"status": "success", "feed_id": feed_id, "feed_global_deleted": not feed_still_used}
    except Exception as e:
        if logger:
            logger.error(f"Error eliminando feed {feed_id} de usuario {user_id}: {e}")
        return {"status": "error", "error": str(e)}

def mark_episode_processed(db, feed_id: str, guid: str, metadata: dict):
    """
    Marca un episodio como procesado en la subcolección processed_episodes de un feed, guardando metadatos y timestamp.
    """
    processed_ref = db.collection("feeds").document(feed_id).collection("processed_episodes").document(guid)
    processed_ref.set({
        "metadata": metadata,
        "processed_at": firestore.SERVER_TIMESTAMP
    }, merge=True)
    return {"status": "success", "feed_id": feed_id, "guid": guid}

def mark_episode_processed(db, feed_id: str, guid: str, metadata: dict):
    """
    Marca un episodio como procesado en la subcolección processed_episodes de un feed, guardando metadatos y timestamp.
    """
    processed_ref = db.collection("feeds").document(feed_id).collection("processed_episodes").document(guid)
    processed_ref.set({
        "metadata": metadata,
        "processed_at": firestore.SERVER_TIMESTAMP
    }, merge=True)
    return {"status": "success", "feed_id": feed_id, "guid": guid}
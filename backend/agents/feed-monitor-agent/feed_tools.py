
"""
Funciones principales (main) para las herramientas del agente Feed Monitor MCP.
Cada función encapsula la lógica de negocio y delega en helpers definidos en feed_utils.py.
"""

from firebase_admin import firestore
from feed_utils import get_feed_id, check_feed_for_new_episodes

def get_user_feeds_main(db, user_id: str):
    """
    Devuelve los feeds de un usuario con información personalizada.
    """
    feeds = []
    user_ref = db.collection("users").document(user_id)
    feeds_ref = user_ref.collection("feeds")
    from feed_utils import serialize_dict_recursively
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
        feeds.append(serialize_dict_recursively(feed_obj))
    return {
        "status": "success",
        "feeds": feeds,
        "count": len(feeds)
    }

def get_all_feeds_main(db):
    """
    Devuelve todos los feeds globales registrados en la colección feeds.
    """
    feeds = []
    feeds_ref = db.collection("feeds")
    from feed_utils import serialize
    for feed_doc in feeds_ref.stream():
        feed_data = feed_doc.to_dict()
        feed_id = feed_doc.id
        feed_obj = {
            "feed_id": feed_id,
            "feed_url": feed_data.get("feed_url", ""),
            "created_at": serialize(feed_data.get("created_at", None)),
            "metadata": feed_data.get("metadata", {}),
        }
        feeds.append(feed_obj)
    return {
        "status": "success",
        "feeds": feeds,
        "count": len(feeds)
    }

def add_feed_to_user_main(db, user_id: str, feed_url: str, custom_name: str = "", active: bool = True, email: str = None):
    """
    Añade un feed RSS a la lista de un usuario y lo registra globalmente si es nuevo.
    """
    feed_id = get_feed_id(feed_url)
    user_ref = db.collection("users").document(user_id)
    user_feed_ref = user_ref.collection("feeds").document(feed_id)
    feed_ref = db.collection("feeds").document(feed_id)
    # Guardar el email como campo adicional en el documento del usuario si se proporciona
    if email:
        user_ref.set({"email": email}, merge=True)
    user_feed_ref.set({
        "active": active,
        "added_at": firestore.SERVER_TIMESTAMP,
        "custom_name": custom_name
    }, merge=True)
    if not feed_ref.get().exists:
        import feedparser
        feed_data = feedparser.parse(feed_url)
        metadata = dict(feed_data.feed)
        feed_ref.set({
            "feed_url": feed_url,
            "metadata": metadata,
            "created_at": firestore.SERVER_TIMESTAMP
        }, merge=True)
    return {"status": "success", "feed_id": feed_id}

def delete_feed_from_user_main(db, user_id: str, feed_url: str, logger=None):
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

def get_new_episodes_main(db, max_episodes=100):
    """
    Devuelve hasta max_episodes episodios nuevos no procesados de todos los feeds globales.
    """
    feeds_result = get_all_feeds_main(db)
    feeds = feeds_result.get('feeds', [])
    all_new_episodes = []
    for feed in feeds:
        if len(all_new_episodes) >= max_episodes:
            break
        feed_url = feed['feed_url']
        new_episodes = check_feed_for_new_episodes(db, feed_url)
        remaining = max_episodes - len(all_new_episodes)
        all_new_episodes.extend(new_episodes[:remaining])
    return {
        "status": "success",
        "total_episodes": len(all_new_episodes),
        "episodes": all_new_episodes
    }

def mark_episode_processed_main(db, feed_id: str, guid: str, metadata: dict):
    """
    Marca un episodio como procesado en la subcolección processed_episodes de un feed.
    """
    processed_ref = db.collection("feeds").document(feed_id).collection("processed_episodes").document(guid)
    processed_ref.set({
        "metadata": metadata,
        "processed_at": firestore.SERVER_TIMESTAMP
    }, merge=True)
    return {"status": "success", "feed_id": feed_id, "guid": guid}

def validate_rss_feed_main(feed_url: str):
    """
    Función principal para validar un RSS feed. Devuelve dict con is_valid, title, description y error si aplica.
    """
    import feedparser
    feed = feedparser.parse(feed_url)
    if feed.bozo:
        error_msg = str(feed.bozo_exception) if hasattr(feed, 'bozo_exception') else "Invalid RSS feed"
        return {
            "is_valid": False,
            "error": error_msg
        }
    title = feed.feed.get("title", "")
    description = feed.feed.get("description", "")
    return {
        "is_valid": True,
        "title": title,
        "description": description
    }
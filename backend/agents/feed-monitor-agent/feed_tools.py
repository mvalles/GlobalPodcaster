"""
Funciones principales (main) para las herramientas del agente Feed Monitor MCP.
Cada función encapsula la lógica de negocio y delega en helpers definidos en feed_utils.py.
"""

from feed_utils import (
    get_user_feeds,
    get_all_feeds,
    add_feed_to_user,
    delete_feed_from_user,
    check_feed_for_new_episodes,
    mark_episode_processed
)

def get_user_feeds_main(db, user_id: str):
    """
    Devuelve los feeds de un usuario con información personalizada.
    """
    feeds = get_user_feeds(db, user_id)
    return {
        "status": "success",
        "feeds": feeds,
        "count": len(feeds)
    }

def get_all_feeds_main(db):
    """
    Devuelve todos los feeds globales registrados en la colección feeds.
    """
    feeds = get_all_feeds(db)
    return {
        "status": "success",
        "feeds": feeds,
        "count": len(feeds)
    }

def add_feed_to_user_main(db, user_id: str, feed_url: str, custom_name: str = "", active: bool = True):
    """
    Añade un feed RSS a la lista de un usuario y lo registra globalmente si es nuevo.
    """
    result = add_feed_to_user(db, user_id, feed_url, custom_name, active)
    return result

def delete_feed_from_user_main(db, user_id: str, feed_url: str):
    """
    Elimina un feed RSS de la lista de un usuario y lo borra globalmente si no lo usa nadie más.
    """
    result = delete_feed_from_user(db, user_id, feed_url)
    return result

def get_new_episodes_main(db, max_episodes=100):
    """
    Devuelve hasta max_episodes episodios nuevos no procesados de todos los feeds globales.
    """
    feeds = get_all_feeds(db)
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
    result = mark_episode_processed(db, feed_id, guid, metadata)
    return result
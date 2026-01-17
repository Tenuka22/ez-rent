import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
from app.data_models import HotelDetails, PropertyListing
from app.utils.logger import logger

# Cache directory path
SCRAPED_DATA_DIR = "./scraped"


def _generate_cache_key(hotel_name: str, adults: int, rooms: int) -> str:
    """
    Generates a unique cache key based on hotel name, adults, and rooms.
    """
    key_string = f"{hotel_name.lower().strip()}_{adults}_{rooms}"
    return hashlib.md5(key_string.encode()).hexdigest()


def _get_cache_filepath(cache_key: str) -> str:
    """
    Returns the full filepath for a cache key.
    """
    return os.path.join(SCRAPED_DATA_DIR, f"{cache_key}.json")


def cache_hotel_data(
    hotel_name: str,
    adults: int,
    rooms: int,
    property_listing: PropertyListing,
    hotel_details: HotelDetails,
) -> None:
    """
    Caches scraped hotel data to a JSON file with a timestamp.
    
    Args:
        hotel_name: The name of the hotel.
        adults: The number of adults.
        rooms: The number of rooms.
        property_listing: The PropertyListing object to cache.
        hotel_details: The HotelDetails object to cache.
    """
    logger.info(
        f"Caching hotel data for '{hotel_name}' (adults={adults}, rooms={rooms})"
    )
    
    try:
        # Create cache directory if it doesn't exist
        if not os.path.exists(SCRAPED_DATA_DIR):
            logger.debug(f"Creating cache directory: {SCRAPED_DATA_DIR}")
            os.makedirs(SCRAPED_DATA_DIR)
        
        cache_key = _generate_cache_key(hotel_name, adults, rooms)
        filepath = _get_cache_filepath(cache_key)
        
        # Prepare cache data
        cache_data = {
            "hotel_name": hotel_name,
            "adults": adults,
            "rooms": rooms,
            "cached_at": datetime.now().isoformat(),
            "property_listing": property_listing.dict() if hasattr(property_listing, 'dict') else property_listing.__dict__,
            "hotel_details": hotel_details.dict() if hasattr(hotel_details, 'dict') else hotel_details.__dict__,
        }
        
        # Write to JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully cached hotel data to {filepath}")
        
    except Exception as e:
        logger.error(f"Error caching hotel data for '{hotel_name}': {e}", exc_info=True)
        # Don't raise - caching failures shouldn't break the scraper


def get_cached_hotel_data(
    hotel_name: str,
    adults: int,
    rooms: int,
    max_age_hours: int = 24,
) -> Optional[Tuple[PropertyListing, HotelDetails]]:
    """
    Retrieves cached hotel data if it exists and is less than max_age_hours old.
    
    Args:
        hotel_name: The name of the hotel.
        adults: The number of adults.
        rooms: The number of rooms.
        max_age_hours: Maximum age of cache in hours (default: 24).
    
    Returns:
        Tuple of (PropertyListing, HotelDetails) if valid cache exists, None otherwise.
    """
    logger.info(
        f"Checking cache for '{hotel_name}' (adults={adults}, rooms={rooms})"
    )
    
    try:
        cache_key = _generate_cache_key(hotel_name, adults, rooms)
        filepath = _get_cache_filepath(cache_key)
        
        if not os.path.exists(filepath):
            logger.debug(f"No cache file found at {filepath}")
            return None
        
        # Read cache file
        with open(filepath, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # Check cache age
        cached_at = datetime.fromisoformat(cache_data["cached_at"])
        cache_age = datetime.now() - cached_at
        
        if cache_age > timedelta(hours=max_age_hours):
            logger.info(
                f"Cache expired (age: {cache_age.total_seconds() / 3600:.1f} hours). "
                f"Removing old cache file."
            )
            os.remove(filepath)
            return None
        
        logger.info(
            f"Found valid cache (age: {cache_age.total_seconds() / 3600:.1f} hours)"
        )
        
        # Reconstruct objects from cached data
        property_listing = PropertyListing(**cache_data["property_listing"])
        hotel_details = HotelDetails(**cache_data["hotel_details"])
        
        return property_listing, hotel_details
        
    except Exception as e:
        logger.warning(
            f"Error reading cache for '{hotel_name}': {e}. Will proceed with fresh scrape.",
            exc_info=True
        )
        return None


def clear_expired_cache(max_age_hours: int = 24) -> int:
    """
    Removes all cache files older than max_age_hours.
    
    Args:
        max_age_hours: Maximum age of cache in hours (default: 24).
    
    Returns:
        Number of files removed.
    """
    if not os.path.exists(SCRAPED_DATA_DIR):
        return 0
    
    removed_count = 0
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    
    try:
        for filename in os.listdir(SCRAPED_DATA_DIR):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(SCRAPED_DATA_DIR, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                cached_at = datetime.fromisoformat(cache_data["cached_at"])
                
                if cached_at < cutoff_time:
                    os.remove(filepath)
                    removed_count += 1
                    logger.debug(f"Removed expired cache file: {filename}")
                    
            except Exception as e:
                logger.warning(f"Error processing cache file {filename}: {e}")
                continue
        
        if removed_count > 0:
            logger.info(f"Cleared {removed_count} expired cache file(s)")
        
        return removed_count
        
    except Exception as e:
        logger.error(f"Error clearing expired cache: {e}", exc_info=True)
        return removed_count
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd

from app.utils.logger import logger
from app.utils.file_io.read_scraped_data_from_csv import read_scraped_data_from_csv
from server.utils import normalize_booking_url


def _extract_metadata_from_path(file_path: str, data_type: str) -> Optional[Dict[str, Any]]:
    """
    Extracts metadata (destination, adults, rooms, limits) from the file path.
    Assumes path format:
    - properties: scraped/properties/{destination}/{adults}/{rooms}/limit_{limit}.csv
    - hotel_details: scraped/hotel_details/{destination}/{adults}/{rooms}/limit_{limit}.csv
    - predictions: scraped/predictions/{model_type}/{destination}/{adults}/{rooms}/props_{props_limit}/details_{details_limit}/predictions_{timestamp}.csv
    """
    try:
        parts = file_path.split(os.sep)
        
        if data_type == "properties":
            if len(parts) < 5: return None
            # e.g., ['scraped', 'properties', 'Unawatuna', '2', '1', 'limit_300.csv']
            destination = parts[-4]
            adults = int(parts[-3])
            rooms = int(parts[-2])
            limit_match = re.match(r"limit_(\d+)\.csv", parts[-1])
            properties_limit = int(limit_match.group(1)) if limit_match else None
            
            if not all([destination, adults, rooms, properties_limit]): return None
            
            return {
                "destination": destination,
                "adults": adults,
                "rooms": rooms,
                "properties_limit": properties_limit,
                "file_mtime": datetime.fromtimestamp(os.path.getmtime(file_path))
            }
        
        elif data_type == "hotel_details":
            if len(parts) < 5: return None
            # e.g., ['scraped', 'hotel_details', 'Unawatuna', '2', '1', 'limit_100.csv']
            destination = parts[-4]
            adults = int(parts[-3])
            rooms = int(parts[-2])
            limit_match = re.match(r"limit_(\d+)\.csv", parts[-1])
            hotel_details_limit = int(limit_match.group(1)) if limit_match else None

            if not all([destination, adults, rooms, hotel_details_limit]): return None
            
            return {
                "destination": destination,
                "adults": adults,
                "rooms": rooms,
                "hotel_details_limit": hotel_details_limit,
                "file_mtime": datetime.fromtimestamp(os.path.getmtime(file_path))
            }

        elif data_type == "predictions":
            if len(parts) < 8: return None
            # e.g., ['scraped', 'predictions', 'basic', 'Unawatuna', '2', '1', 'props_300', 'details_100', 'predictions_20260117_193655.csv']
            model_type = parts[-7]
            destination = parts[-6]
            adults = int(parts[-5])
            rooms = int(parts[-4])
            props_limit_match = re.match(r"props_(\d+)", parts[-3])
            properties_limit = int(props_limit_match.group(1)) if props_limit_match else None
            details_limit_match = re.match(r"details_(\d+)", parts[-2])
            hotel_details_limit = int(details_limit_match.group(1)) if details_limit_match else None
            
            filename_match = re.match(r"predictions_(\d{8}_\d{6})\.csv", parts[-1])
            timestamp_str = filename_match.group(1) if filename_match else None
            
            if not all([model_type, destination, adults, rooms, properties_limit, hotel_details_limit, timestamp_str]): return None
            
            return {
                "model_type": model_type,
                "destination": destination,
                "adults": adults,
                "rooms": rooms,
                "properties_limit": properties_limit,
                "hotel_details_limit": hotel_details_limit,
                "timestamp": datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S"),
                "filename": parts[-1],
                "full_path": file_path,
                "file_mtime": datetime.fromtimestamp(os.path.getmtime(file_path))
            }
            
    except (ValueError, IndexError, AttributeError) as e:
        logger.warning(f"Could not extract metadata from path {file_path} for type {data_type}: {e}")
        return None


def _load_and_process_csvs(base_dir: str, data_type: str) -> pd.DataFrame:
    """
    Loads all CSVs of a given data_type from the base_dir, extracts metadata,
    and returns a concatenated DataFrame.
    """
    all_data = []
    full_base_path = os.path.join("scraped", base_dir)

    if not os.path.isdir(full_base_path):
        logger.warning(f"Base path not found: {full_base_path}")
        return pd.DataFrame()

    for root, _, files in os.walk(full_base_path):
        for file in files:
            if file.endswith(".csv"):
                file_path = os.path.join(root, file)
                metadata = _extract_metadata_from_path(file_path, data_type)
                
                if metadata:
                    try:
                        df = read_scraped_data_from_csv(file_path, is_hotel_detail=(data_type == "hotel_details"))
                        df = df.assign(**metadata)
                        all_data.append(df)
                    except Exception as e:
                        logger.error(f"Error reading {file_path}: {e}")
    
    if not all_data:
        return pd.DataFrame()
    
    combined_df = pd.concat(all_data, ignore_index=True)
    return combined_df


def get_all_properties_data() -> pd.DataFrame:
    """Loads and returns all properties data from scraped files."""
    return _load_and_process_csvs("properties", "properties")


def get_all_hotel_details_data() -> pd.DataFrame:
    """Loads and returns all hotel details data from scraped files."""
    df_details = _load_and_process_csvs("hotel_details", "hotel_details")
    if not df_details.empty:
        df_details["normalized_url"] = df_details["url"].apply(normalize_booking_url)
    return df_details


def get_all_predictions_data() -> pd.DataFrame:
    """Loads and returns all prediction data from scraped files."""
    return _load_and_process_csvs("predictions", "predictions")


def deduplicate_by_latest(df: pd.DataFrame, key_cols: List[str], timestamp_col: str) -> pd.DataFrame:
    """
    Deduplicates a DataFrame by keeping the row with the latest timestamp
    for each unique combination of key_cols.
    """
    if df.empty:
        return pd.DataFrame()
    
    df_sorted = df.sort_values(by=timestamp_col, ascending=False)
    df_deduplicated = df_sorted.drop_duplicates(subset=key_cols, keep="first")
    return df_deduplicated

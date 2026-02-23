#!/usr/bin/env python3
"""
SAP Security Log Data Ingestion Script
=======================================
Reads SAP security logs from Excel, transforms the data, and indexes into Elasticsearch.

Author: SecurityBridgeAI
Python Version: 3.10+
"""

import sys
from datetime import datetime
from typing import Generator, Any

import pandas as pd
from elasticsearch import Elasticsearch, helpers
from tqdm import tqdm

ES_HOST = "http://localhost:9200"
ES_INDEX = "sap-security-logs"


DATA_FILE = "data123.xlsx"

# Batch size for bulk indexing
BATCH_SIZE = 500


# =============================================================================
# ELASTICSEARCH INDEX MAPPING
# =============================================================================

INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "refresh_interval": "5s"
    },
    "mappings": {
        "properties": {
            # Timestamp (merged from Date + Time)
            "@timestamp": {"type": "date"},
            
            # System fields (keyword for exact filtering & aggregations)
            "System": {"type": "keyword"},
            "Client": {"type": "keyword"},
            "CompanyCode": {"type": "keyword"},
            "Listener": {"type": "keyword"},
            
            # Severity fields
            "Severity": {"type": "keyword"},
            "SeverityNum": {"type": "integer"},
            
            # Event details (keyword for aggregations)
            "Action": {"type": "keyword"},
            "Program": {"type": "keyword"},
            "Transaction": {"type": "keyword"},
            
            # User information
            "User": {"type": "keyword"},
            "UserName": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "UserGroup": {"type": "keyword"},
            
            # Network information
            "Terminal": {"type": "keyword"},
            "FQDN": {"type": "keyword"},
            
            # Message (full-text search)
            "Message": {
                "type": "text",
                "analyzer": "standard",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 512
                    }
                }
            },
            
            # Additional metadata
            "Incidents": {"type": "float"},
            "PrivilegeAccessMode": {"type": "keyword"},
            "EventTags": {"type": "keyword"}
        }
    }
}


# =============================================================================
# DATA TRANSFORMATION FUNCTIONS
# =============================================================================

def parse_datetime(date_str: str, time_str: str) -> str:
    """
    Merge Date and Time columns into ISO 8601 format timestamp.
    
    Args:
        date_str: Date in DD.MM.YYYY format
        time_str: Time in HH:MM:SS format
    
    Returns:
        ISO 8601 formatted datetime string
    
    Example:
        >>> parse_datetime("04.02.2026", "14:30:00")
        "2026-02-04T14:30:00"
    """
    try:
        # Handle various date formats
        if pd.isna(date_str) or pd.isna(time_str):
            return datetime.now().isoformat()
        
        date_str = str(date_str).strip()
        time_str = str(time_str).strip()
        
        # Parse DD.MM.YYYY format
        if "." in date_str:
            day, month, year = date_str.split(".")
            # Handle 2-digit year
            if len(year) == 2:
                year = f"20{year}"
        else:
            # Fallback: try pandas parsing
            dt = pd.to_datetime(f"{date_str} {time_str}")
            return dt.isoformat()
        
        # Handle time with or without seconds
        time_parts = time_str.split(":")
        if len(time_parts) == 2:
            time_str = f"{time_str}:00"
        
        # Construct ISO format
        iso_datetime = f"{year}-{month.zfill(2)}-{day.zfill(2)}T{time_str}"
        
        # Validate by parsing
        datetime.fromisoformat(iso_datetime)
        return iso_datetime
        
    except (ValueError, AttributeError, TypeError) as e:
        print(f"  ⚠️  Date parsing warning: {date_str} {time_str} -> {e}")
        return datetime.now().isoformat()


def transform_row(row: pd.Series) -> dict[str, Any]:
    """
    Transform a pandas row into an Elasticsearch document.
    
    Args:
        row: A pandas Series representing one log entry
    
    Returns:
        Dictionary suitable for ES indexing
    """
    # Safely get values with fallbacks
    def safe_str(val):
        if pd.isna(val):
            return None
        return str(val).strip() if val else None
    
    def safe_float(val):
        if pd.isna(val):
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    
    def safe_int(val):
        if pd.isna(val):
            return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None
    
    # Build document
    doc = {
        "@timestamp": parse_datetime(row.get("Date", ""), row.get("Time", "")),
        "System": safe_str(row.get("System")),
        "Client": safe_str(row.get("Client")),
        "CompanyCode": safe_str(row.get("CompanyCode", "1000")),
        "Listener": safe_str(row.get("Listener")),
        "Severity": safe_str(row.get("SeverityTxt")),
        "SeverityNum": safe_int(row.get("Severity")),
        "Action": safe_str(row.get("Action")),
        "Program": safe_str(row.get("Program")),
        "Transaction": safe_str(row.get("Transaction")),
        "User": safe_str(row.get("User")),
        "UserName": safe_str(row.get("User Name")),
        "UserGroup": safe_str(row.get("User Group")),
        "Terminal": safe_str(row.get("Terminal")),
        "FQDN": safe_str(row.get("FQDN")),
        "Message": safe_str(row.get("Message")),
        "Incidents": safe_float(row.get("Incidents")),
        "PrivilegeAccessMode": safe_str(row.get("Privilege Access mode")),
        "EventTags": safe_str(row.get("Event Tags"))
    }
    
    # Remove None values to save space
    return {k: v for k, v in doc.items() if v is not None}


def generate_bulk_actions(df: pd.DataFrame, index_name: str) -> Generator[dict, None, None]:
    """
    Generate bulk indexing actions from DataFrame.
    
    Args:
        df: pandas DataFrame with log data
        index_name: Target Elasticsearch index name
    
    Yields:
        Bulk action dictionaries
    """
    for idx, row in df.iterrows():
        doc = transform_row(row)
        yield {
            "_index": index_name,
            "_id": f"{doc.get('System', 'UNK')}_{doc.get('@timestamp', '')}_{idx}",
            "_source": doc
        }


# =============================================================================
# ELASTICSEARCH OPERATIONS
# =============================================================================

def create_index(es: Elasticsearch, index_name: str) -> None:
    """
    Create Elasticsearch index with mapping. Delete if exists.
    
    Args:
        es: Elasticsearch client instance
        index_name: Name of the index to create
    """
    # Delete existing index if present
    if es.indices.exists(index=index_name):
        print(f"🗑️  Deleting existing index: {index_name}")
        es.indices.delete(index=index_name)
    
    # Create new index with mapping
    print(f"📝 Creating index: {index_name}")
    es.indices.create(index=index_name, body=INDEX_MAPPING)
    print(f"✅ Index created successfully with mapping")


def bulk_index_data(es: Elasticsearch, df: pd.DataFrame, index_name: str) -> tuple[int, int]:
    """
    Bulk index data into Elasticsearch.
    
    Args:
        es: Elasticsearch client instance
        df: pandas DataFrame with log data
        index_name: Target index name
    
    Returns:
        Tuple of (success_count, error_count)
    """
    success_count = 0
    error_count = 0
    
    print(f"📤 Indexing {len(df)} documents...")
    
    # Use tqdm for progress bar
    actions = list(generate_bulk_actions(df, index_name))
    
    # Bulk index with progress tracking
    with tqdm(total=len(actions), desc="Indexing", unit="docs") as pbar:
        for ok, result in helpers.streaming_bulk(
            es,
            actions,
            chunk_size=BATCH_SIZE,
            raise_on_error=False
        ):
            if ok:
                success_count += 1
            else:
                error_count += 1
                print(f"  ❌ Error: {result}")
            pbar.update(1)
    
    return success_count, error_count


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main() -> int:
    """
    Main entry point for data ingestion.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("=" * 60)
    print("SAP Security Log Ingestion - SecurityBridgeAI")
    print("=" * 60)
    print()
    
    # Step 1: Connect to Elasticsearch
    print("🔌 Connecting to Elasticsearch...")
    try:
        es = Elasticsearch(ES_HOST)
        info = es.info()
        print(f"✅ Connected to Elasticsearch {info['version']['number']}")
    except Exception as e:
        print(f"❌ Failed to connect to Elasticsearch: {e}")
        print("   Make sure Elasticsearch is running: docker-compose up -d")
        return 1
    
    print()
    
    # Step 2: Read Excel data
    print(f"📖 Reading data from: {DATA_FILE}")
    try:
        df = pd.read_excel(DATA_FILE)
        print(f"✅ Loaded {len(df)} rows with {len(df.columns)} columns")
        print(f"   Columns: {', '.join(df.columns.tolist())}")
    except FileNotFoundError:
        print(f"❌ File not found: {DATA_FILE}")
        return 1
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        return 1
    
    print()
    
    # Step 3: Create index
    try:
        create_index(es, ES_INDEX)
    except Exception as e:
        print(f"❌ Failed to create index: {e}")
        return 1
    
    print()
    
    # Step 4: Bulk index data
    try:
        success, errors = bulk_index_data(es, df, ES_INDEX)
        print()
        print(f"📊 Indexing Results:")
        print(f"   ✅ Successfully indexed: {success} documents")
        if errors:
            print(f"   ❌ Failed: {errors} documents")
    except Exception as e:
        print(f"❌ Bulk indexing failed: {e}")
        return 1
    
    # Step 5: Refresh index
    print()
    print("🔄 Refreshing index...")
    es.indices.refresh(index=ES_INDEX)
    
    # Step 6: Verify
    count = es.count(index=ES_INDEX)
    print(f"✅ Index contains {count['count']} documents")
    
    print()
    print("=" * 60)
    print("✅ Data ingestion completed successfully!")
    print(f"   Index: {ES_INDEX}")
    print(f"   Documents: {count['count']}")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

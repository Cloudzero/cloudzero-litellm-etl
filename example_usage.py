#!/usr/bin/env python3
"""Example usage of the LiteLLM to CloudZero ETL tool."""

import subprocess
import sys


def main():
    """Demonstrate example usage patterns."""
    
    print("LiteLLM to CloudZero ETL Tool - Example Usage")
    print("=" * 50)
    
    # Example database connection string (replace with your actual values)
    db_connection = "postgresql://user:password@localhost:5432/litellm_db"
    
    print("\n1. Analysis Mode - Analyze 100 records:")
    print("litellm-cz-etl --input 'postgresql://user:pass@host:5432/db' --analysis 100")
    
    print("\n2. Analysis Mode with JSON output:")
    print("litellm-cz-etl --input 'postgresql://user:pass@host:5432/db' --analysis 100 --json analysis_results.json")
    
    print("\n3. Export to CSV:")
    print("litellm-cz-etl --input 'postgresql://user:pass@host:5432/db' --csv output.csv")
    
    print("\n4. Send to CloudZero AnyCost API:")
    print("litellm-cz-etl --input 'postgresql://user:pass@host:5432/db' --cz-api-key 'your-api-key' --cz-connection-id 'your-connection-id'")
    
    print("\nNote: Replace the database connection string with your actual LiteLLM database credentials.")
    print("For CloudZero integration, obtain your API key and connection ID from the CloudZero dashboard.")


if __name__ == "__main__":
    main()
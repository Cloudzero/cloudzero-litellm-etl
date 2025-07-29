#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Create a test SQLite database with sample LiteLLM data.

This script creates a SQLite database with anonymized test data.
All names, emails, and API keys are fake and for testing purposes only.
No real PII or sensitive data is included.
"""

import sqlite3
from datetime import datetime, timedelta
import random
import os

def create_test_database(db_path: str = "test.sqlite"):
    """Create a test SQLite database with all LiteLLM tables and sample data."""
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Create tables
    
    # Organizations
    cursor.execute("""
    CREATE TABLE LiteLLM_OrganizationTable (
        organization_id TEXT PRIMARY KEY,
        organization_alias TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Teams
    cursor.execute("""
    CREATE TABLE LiteLLM_TeamTable (
        team_id TEXT PRIMARY KEY,
        team_alias TEXT,
        organization_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (organization_id) REFERENCES LiteLLM_OrganizationTable(organization_id)
    )
    """)
    
    # Users
    cursor.execute("""
    CREATE TABLE LiteLLM_UserTable (
        user_id TEXT PRIMARY KEY,
        user_alias TEXT,
        user_email TEXT,
        team_id TEXT,
        organization_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (team_id) REFERENCES LiteLLM_TeamTable(team_id),
        FOREIGN KEY (organization_id) REFERENCES LiteLLM_OrganizationTable(organization_id)
    )
    """)
    
    # Verification Tokens (API Keys)
    cursor.execute("""
    CREATE TABLE LiteLLM_VerificationToken (
        token TEXT PRIMARY KEY,
        key_name TEXT,
        key_alias TEXT,
        user_id TEXT,
        team_id TEXT,
        organization_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES LiteLLM_UserTable(user_id),
        FOREIGN KEY (team_id) REFERENCES LiteLLM_TeamTable(team_id),
        FOREIGN KEY (organization_id) REFERENCES LiteLLM_OrganizationTable(organization_id)
    )
    """)
    
    # Daily User Spend
    cursor.execute("""
    CREATE TABLE LiteLLM_DailyUserSpend (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL,
        user_id TEXT NOT NULL,
        api_key TEXT,
        model TEXT,
        model_group TEXT,
        custom_llm_provider TEXT,
        prompt_tokens INTEGER DEFAULT 0,
        completion_tokens INTEGER DEFAULT 0,
        spend DECIMAL(10, 6) DEFAULT 0,
        api_requests INTEGER DEFAULT 0,
        successful_requests INTEGER DEFAULT 0,
        failed_requests INTEGER DEFAULT 0,
        cache_creation_input_tokens INTEGER DEFAULT 0,
        cache_read_input_tokens INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES LiteLLM_UserTable(user_id),
        FOREIGN KEY (api_key) REFERENCES LiteLLM_VerificationToken(token)
    )
    """)
    
    # Daily Team Spend
    cursor.execute("""
    CREATE TABLE LiteLLM_DailyTeamSpend (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL,
        team_id TEXT NOT NULL,
        api_key TEXT,
        model TEXT,
        model_group TEXT,
        custom_llm_provider TEXT,
        prompt_tokens INTEGER DEFAULT 0,
        completion_tokens INTEGER DEFAULT 0,
        spend DECIMAL(10, 6) DEFAULT 0,
        api_requests INTEGER DEFAULT 0,
        successful_requests INTEGER DEFAULT 0,
        failed_requests INTEGER DEFAULT 0,
        cache_creation_input_tokens INTEGER DEFAULT 0,
        cache_read_input_tokens INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (team_id) REFERENCES LiteLLM_TeamTable(team_id),
        FOREIGN KEY (api_key) REFERENCES LiteLLM_VerificationToken(token)
    )
    """)
    
    # Daily Tag Spend
    cursor.execute("""
    CREATE TABLE LiteLLM_DailyTagSpend (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL,
        tag TEXT NOT NULL,
        api_key TEXT,
        model TEXT,
        model_group TEXT,
        custom_llm_provider TEXT,
        prompt_tokens INTEGER DEFAULT 0,
        completion_tokens INTEGER DEFAULT 0,
        spend DECIMAL(10, 6) DEFAULT 0,
        api_requests INTEGER DEFAULT 0,
        successful_requests INTEGER DEFAULT 0,
        failed_requests INTEGER DEFAULT 0,
        cache_creation_input_tokens INTEGER DEFAULT 0,
        cache_read_input_tokens INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (api_key) REFERENCES LiteLLM_VerificationToken(token)
    )
    """)
    
    # Spend Logs
    cursor.execute("""
    CREATE TABLE LiteLLM_SpendLogs (
        request_id TEXT PRIMARY KEY,
        call_type TEXT,
        api_key TEXT,
        spend DECIMAL(10, 6),
        total_tokens INTEGER,
        prompt_tokens INTEGER,
        completion_tokens INTEGER,
        startTime TIMESTAMP,
        endTime TIMESTAMP,
        completionStartTime TIMESTAMP,
        model TEXT,
        model_group TEXT,
        custom_llm_provider TEXT,
        user TEXT,
        team_id TEXT,
        end_user TEXT,
        cache_hit BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (api_key) REFERENCES LiteLLM_VerificationToken(token),
        FOREIGN KEY (user) REFERENCES LiteLLM_UserTable(user_id),
        FOREIGN KEY (team_id) REFERENCES LiteLLM_TeamTable(team_id)
    )
    """)
    
    # Insert sample data
    
    # Organizations (anonymized)
    orgs = [
        ("org-001", "Test Org Alpha"),
        ("org-002", "Test Org Beta"),
        ("org-003", "Test Org Gamma")
    ]
    cursor.executemany("INSERT INTO LiteLLM_OrganizationTable (organization_id, organization_alias) VALUES (?, ?)", orgs)
    
    # Teams (generic names)
    teams = [
        ("team-001", "Team A", "org-001"),
        ("team-002", "Team B", "org-001"),
        ("team-003", "Team C", "org-002"),
        ("team-004", "Team D", "org-003"),
        ("team-005", "Team E", "org-003")
    ]
    cursor.executemany("INSERT INTO LiteLLM_TeamTable (team_id, team_alias, organization_id) VALUES (?, ?, ?)", teams)
    
    # Users (fully anonymized - no real names or emails)
    users = [
        ("user-001", "test_user_001", "user001@example.test", "team-001", "org-001"),
        ("user-002", "test_user_002", "user002@example.test", "team-001", "org-001"),
        ("user-003", "test_user_003", "user003@example.test", "team-002", "org-001"),
        ("user-004", "test_user_004", "user004@example.test", "team-003", "org-002"),
        ("user-005", "test_user_005", "user005@example.test", "team-004", "org-003"),
        ("user-006", "test_user_006", "user006@example.test", "team-005", "org-003")
    ]
    cursor.executemany("INSERT INTO LiteLLM_UserTable (user_id, user_alias, user_email, team_id, organization_id) VALUES (?, ?, ?, ?, ?)", users)
    
    # API Keys (obfuscated - not real API key patterns)
    api_keys = [
        ("test-key-" + "x" * 32 + "-001", "test-prod-key", "prod-key", "user-001", "team-001", "org-001"),
        ("test-key-" + "x" * 32 + "-002", "test-dev-key", "dev-key", "user-002", "team-001", "org-001"),
        ("test-key-" + "x" * 32 + "-003", "test-ml-key", "ml-key", "user-003", "team-002", "org-001"),
        ("test-key-" + "x" * 32 + "-004", "test-product-key", "product", "user-004", "team-003", "org-002"),
        ("test-key-" + "x" * 32 + "-005", "test-devops-key", "devops", "user-005", "team-004", "org-003"),
        ("test-key-" + "x" * 32 + "-006", "test-ml-prod-key", "ml-prod", "user-006", "team-005", "org-003")
    ]
    cursor.executemany("INSERT INTO LiteLLM_VerificationToken (token, key_name, key_alias, user_id, team_id, organization_id) VALUES (?, ?, ?, ?, ?, ?)", api_keys)
    
    # Generate sample spend data for the last 30 days
    models = [
        ("gpt-4", "openai-gpt-4", "openai"),
        ("gpt-3.5-turbo", "openai-gpt-3.5", "openai"),
        ("claude-3-opus", "anthropic-claude-3", "anthropic"),
        ("claude-3-sonnet", "anthropic-claude-3", "anthropic"),
        ("llama-2-70b", "meta-llama-2", "together_ai"),
        ("mixtral-8x7b", "mixtral", "groq")
    ]
    
    start_date = datetime.now() - timedelta(days=30)
    
    # Generate daily user spend data
    user_spend_data = []
    for day in range(30):
        current_date = start_date + timedelta(days=day)
        for user_id, _, _, team_id, _ in users:
            for _ in range(random.randint(0, 3)):  # 0-3 entries per user per day
                model, model_group, provider = random.choice(models)
                api_key = random.choice([k[0] for k in api_keys if k[3] == user_id])
                prompt_tokens = random.randint(100, 5000)
                completion_tokens = random.randint(50, 2000)
                requests = random.randint(1, 50)
                successful = int(requests * random.uniform(0.9, 1.0))
                failed = requests - successful
                
                # Calculate spend based on tokens (simplified pricing)
                spend = (prompt_tokens * 0.00003 + completion_tokens * 0.00006) * requests
                
                user_spend_data.append((
                    current_date.date(),
                    user_id,
                    api_key,
                    model,
                    model_group,
                    provider,
                    prompt_tokens * requests,
                    completion_tokens * requests,
                    spend,
                    requests,
                    successful,
                    failed,
                    random.randint(0, 1000),
                    random.randint(0, 500)
                ))
    
    cursor.executemany("""
        INSERT INTO LiteLLM_DailyUserSpend 
        (date, user_id, api_key, model, model_group, custom_llm_provider, 
         prompt_tokens, completion_tokens, spend, api_requests, 
         successful_requests, failed_requests, cache_creation_input_tokens, cache_read_input_tokens)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, user_spend_data)
    
    # Generate daily team spend data
    team_spend_data = []
    for day in range(30):
        current_date = start_date + timedelta(days=day)
        for team_id, _, _ in teams:
            for _ in range(random.randint(1, 2)):  # 1-2 entries per team per day
                model, model_group, provider = random.choice(models)
                # Get random API key from team members
                team_keys = [k[0] for k in api_keys if k[4] == team_id]
                if team_keys:
                    api_key = random.choice(team_keys)
                else:
                    api_key = random.choice([k[0] for k in api_keys])
                
                prompt_tokens = random.randint(1000, 20000)
                completion_tokens = random.randint(500, 10000)
                requests = random.randint(10, 200)
                successful = int(requests * random.uniform(0.95, 1.0))
                failed = requests - successful
                
                spend = (prompt_tokens * 0.00003 + completion_tokens * 0.00006) * requests
                
                team_spend_data.append((
                    current_date.date(),
                    team_id,
                    api_key,
                    model,
                    model_group,
                    provider,
                    prompt_tokens * requests,
                    completion_tokens * requests,
                    spend,
                    requests,
                    successful,
                    failed,
                    random.randint(0, 5000),
                    random.randint(0, 2000)
                ))
    
    cursor.executemany("""
        INSERT INTO LiteLLM_DailyTeamSpend 
        (date, team_id, api_key, model, model_group, custom_llm_provider, 
         prompt_tokens, completion_tokens, spend, api_requests, 
         successful_requests, failed_requests, cache_creation_input_tokens, cache_read_input_tokens)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, team_spend_data)
    
    # Generate spend logs (recent transactions)
    spend_logs_data = []
    for i in range(100):  # 100 recent transactions
        request_id = f"req-{i:04d}"
        user_id = random.choice([u[0] for u in users])
        team_id = next(u[3] for u in users if u[0] == user_id)
        api_key = random.choice([k[0] for k in api_keys if k[3] == user_id])
        model, model_group, provider = random.choice(models)
        
        start_time = datetime.now() - timedelta(hours=random.randint(1, 72))
        end_time = start_time + timedelta(seconds=random.uniform(0.5, 5.0))
        completion_start_time = start_time + timedelta(seconds=random.uniform(0.1, 0.5))
        
        prompt_tokens = random.randint(100, 2000)
        completion_tokens = random.randint(50, 1000)
        total_tokens = prompt_tokens + completion_tokens
        
        spend = prompt_tokens * 0.00003 + completion_tokens * 0.00006
        
        spend_logs_data.append((
            request_id,
            "completion",
            api_key,
            spend,
            total_tokens,
            prompt_tokens,
            completion_tokens,
            start_time,
            end_time,
            completion_start_time,
            model,
            model_group,
            provider,
            user_id,
            team_id,
            f"test-enduser-{random.randint(1, 20)}",
            random.choice([0, 1])  # cache_hit
        ))
    
    cursor.executemany("""
        INSERT INTO LiteLLM_SpendLogs 
        (request_id, call_type, api_key, spend, total_tokens, prompt_tokens, completion_tokens,
         startTime, endTime, completionStartTime, model, model_group, custom_llm_provider,
         user, team_id, end_user, cache_hit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, spend_logs_data)
    
    # Create indexes for better performance
    cursor.execute("CREATE INDEX idx_user_spend_date ON LiteLLM_DailyUserSpend(date)")
    cursor.execute("CREATE INDEX idx_user_spend_user ON LiteLLM_DailyUserSpend(user_id)")
    cursor.execute("CREATE INDEX idx_team_spend_date ON LiteLLM_DailyTeamSpend(date)")
    cursor.execute("CREATE INDEX idx_team_spend_team ON LiteLLM_DailyTeamSpend(team_id)")
    cursor.execute("CREATE INDEX idx_spend_logs_start ON LiteLLM_SpendLogs(startTime)")
    cursor.execute("CREATE INDEX idx_spend_logs_user ON LiteLLM_SpendLogs(user)")
    
    # Commit and close
    conn.commit()
    conn.close()
    
    print(f"Test SQLite database created at: {db_path}")
    print(f"Database contains:")
    print(f"  - {len(orgs)} organizations")
    print(f"  - {len(teams)} teams")
    print(f"  - {len(users)} users")
    print(f"  - {len(api_keys)} API keys")
    print(f"  - {len(user_spend_data)} daily user spend records")
    print(f"  - {len(team_spend_data)} daily team spend records")
    print(f"  - {len(spend_logs_data)} spend log entries")


if __name__ == "__main__":
    create_test_database()
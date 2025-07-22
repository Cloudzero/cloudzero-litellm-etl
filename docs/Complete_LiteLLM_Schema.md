# Complete LiteLLM Database Schema Documentation

## Overview

This document provides a comprehensive overview of all 24 LiteLLM tables discovered in the database.

## Table Summary

| Table Name | Columns | Rows | Primary Keys | Foreign Keys | Indexes |
|------------|---------|------|--------------|--------------|---------|
| LiteLLM_AuditLog | 9 | 0 | id | 0 | 1 |
| LiteLLM_BudgetTable | 13 | 6 | budget_id | 0 | 1 |
| LiteLLM_Config | 2 | 1 | param_name | 0 | 1 |
| LiteLLM_CredentialsTable | 8 | 0 | credential_id | 0 | 2 |
| LiteLLM_CronJob | 5 | 0 | cronjob_id | 0 | 1 |
| LiteLLM_DailyTagSpend | 17 | 0 | id | 0 | 6 |
| LiteLLM_DailyTeamSpend | 17 | 66 | id | 0 | 6 |
| LiteLLM_DailyUserSpend | 17 | 118 | id | 0 | 6 |
| LiteLLM_EndUserTable | 7 | 1 | user_id | 1 | 1 |
| LiteLLM_ErrorLogs | 11 | 0 | request_id | 0 | 1 |
| LiteLLM_InvitationLink | 9 | 27 | id | 3 | 1 |
| LiteLLM_ManagedFileTable | 6 | 0 | id | 0 | 3 |
| LiteLLM_ManagedVectorStoresTable | 8 | 0 | vector_store_id | 0 | 1 |
| LiteLLM_ModelTable | 6 | 4 | id | 0 | 1 |
| LiteLLM_OrganizationMembership | 7 | 0 | user_id, organization_id | 3 | 2 |
| LiteLLM_OrganizationTable | 11 | 4 | organization_id | 1 | 1 |
| LiteLLM_ProxyModelTable | 8 | 0 | model_id | 0 | 1 |
| LiteLLM_SpendLogs | 27 | 25 | request_id | 0 | 3 |
| LiteLLM_TeamMembership | 4 | 0 | user_id, team_id | 1 | 1 |
| LiteLLM_TeamTable | 22 | 4 | team_id | 2 | 2 |
| LiteLLM_UserNotifications | 5 | 0 | request_id | 0 | 1 |
| LiteLLM_UserTable | 23 | 37 | user_id | 1 | 2 |
| LiteLLM_VerificationToken | 30 | 180 | token | 2 | 1 |
| LiteLLM_VerificationTokenView | 33 | 180 | None | 0 | 0 |

## Detailed Table Schemas

### LiteLLM_AuditLog

**Row Count:** 0

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| id | text | NO | None |  |
| updated_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| changed_by | text | NO | ''::text |  |
| changed_by_api_key | text | NO | ''::text |  |
| action | text | NO | None |  |
| table_name | text | NO | None |  |
| object_id | text | NO | None |  |
| before_value | jsonb | YES | None |  |
| updated_values | jsonb | YES | None |  |

#### Primary Keys

- `id`

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_AuditLog_pkey | id | YES |

---

### LiteLLM_BudgetTable

**Row Count:** 6

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| budget_id | text | NO | None |  |
| max_budget | double precision(53) | YES | None | 53 |
| soft_budget | double precision(53) | YES | None | 53 |
| max_parallel_requests | integer(32) | YES | None | 32 |
| tpm_limit | bigint(64) | YES | None | 64 |
| rpm_limit | bigint(64) | YES | None | 64 |
| model_max_budget | jsonb | YES | None |  |
| budget_duration | text | YES | None |  |
| budget_reset_at | timestamp without time zone | YES | None |  |
| created_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| created_by | text | NO | None |  |
| updated_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| updated_by | text | NO | None |  |

#### Primary Keys

- `budget_id`

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_BudgetTable_pkey | budget_id | YES |

---

### LiteLLM_Config

**Row Count:** 1

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| param_name | text | NO | None |  |
| param_value | jsonb | YES | None |  |

#### Primary Keys

- `param_name`

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_Config_pkey | param_name | YES |

---

### LiteLLM_CredentialsTable

**Row Count:** 0

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| credential_id | text | NO | None |  |
| credential_name | text | NO | None |  |
| credential_values | jsonb | NO | None |  |
| credential_info | jsonb | YES | None |  |
| created_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| created_by | text | NO | None |  |
| updated_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| updated_by | text | NO | None |  |

#### Primary Keys

- `credential_id`

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_CredentialsTable_credential_name_key | credential_name | YES |
| LiteLLM_CredentialsTable_pkey | credential_id | YES |

---

### LiteLLM_CronJob

**Row Count:** 0

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| cronjob_id | text | NO | None |  |
| pod_id | text | NO | None |  |
| status | USER-DEFINED | NO | 'INACTIVE'::"JobStatus" |  |
| last_updated | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| ttl | timestamp without time zone | NO | None |  |

#### Primary Keys

- `cronjob_id`

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_CronJob_pkey | cronjob_id | YES |

---

### LiteLLM_DailyTagSpend

**Row Count:** 0

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| id | text | NO | None |  |
| tag | text | NO | None |  |
| date | text | NO | None |  |
| api_key | text | NO | None |  |
| model | text | NO | None |  |
| model_group | text | YES | None |  |
| custom_llm_provider | text | YES | None |  |
| prompt_tokens | integer(32) | NO | 0 | 32 |
| completion_tokens | integer(32) | NO | 0 | 32 |
| cache_read_input_tokens | integer(32) | NO | 0 | 32 |
| cache_creation_input_tokens | integer(32) | NO | 0 | 32 |
| spend | double precision(53) | NO | 0.0 | 53 |
| api_requests | integer(32) | NO | 0 | 32 |
| successful_requests | integer(32) | NO | 0 | 32 |
| failed_requests | integer(32) | NO | 0 | 32 |
| created_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| updated_at | timestamp without time zone | NO | None |  |

#### Primary Keys

- `id`

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_DailyTagSpend_api_key_idx | api_key | NO |
| LiteLLM_DailyTagSpend_date_idx | date | NO |
| LiteLLM_DailyTagSpend_model_idx | model | NO |
| LiteLLM_DailyTagSpend_pkey | id | YES |
| LiteLLM_DailyTagSpend_tag_date_api_key_model_custom_llm_pro_key | tag, date, api_key, model, custom_llm_provider | YES |
| LiteLLM_DailyTagSpend_tag_idx | tag | NO |

---

### LiteLLM_DailyTeamSpend

**Row Count:** 66

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| id | text | NO | None |  |
| team_id | text | NO | None |  |
| date | text | NO | None |  |
| api_key | text | NO | None |  |
| model | text | NO | None |  |
| model_group | text | YES | None |  |
| custom_llm_provider | text | YES | None |  |
| prompt_tokens | integer(32) | NO | 0 | 32 |
| completion_tokens | integer(32) | NO | 0 | 32 |
| spend | double precision(53) | NO | 0.0 | 53 |
| api_requests | integer(32) | NO | 0 | 32 |
| successful_requests | integer(32) | NO | 0 | 32 |
| failed_requests | integer(32) | NO | 0 | 32 |
| created_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| updated_at | timestamp without time zone | NO | None |  |
| cache_creation_input_tokens | integer(32) | NO | 0 | 32 |
| cache_read_input_tokens | integer(32) | NO | 0 | 32 |

#### Primary Keys

- `id`

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_DailyTeamSpend_api_key_idx | api_key | NO |
| LiteLLM_DailyTeamSpend_date_idx | date | NO |
| LiteLLM_DailyTeamSpend_model_idx | model | NO |
| LiteLLM_DailyTeamSpend_pkey | id | YES |
| LiteLLM_DailyTeamSpend_team_id_date_api_key_model_custom_ll_key | team_id, date, api_key, model, custom_llm_provider | YES |
| LiteLLM_DailyTeamSpend_team_id_idx | team_id | NO |

---

### LiteLLM_DailyUserSpend

**Row Count:** 118

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| id | text | NO | None |  |
| user_id | text | NO | None |  |
| date | text | NO | None |  |
| api_key | text | NO | None |  |
| model | text | NO | None |  |
| model_group | text | YES | None |  |
| custom_llm_provider | text | YES | None |  |
| prompt_tokens | integer(32) | NO | 0 | 32 |
| completion_tokens | integer(32) | NO | 0 | 32 |
| spend | double precision(53) | NO | 0.0 | 53 |
| created_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| updated_at | timestamp without time zone | NO | None |  |
| api_requests | integer(32) | NO | 0 | 32 |
| failed_requests | integer(32) | NO | 0 | 32 |
| successful_requests | integer(32) | NO | 0 | 32 |
| cache_creation_input_tokens | integer(32) | NO | 0 | 32 |
| cache_read_input_tokens | integer(32) | NO | 0 | 32 |

#### Primary Keys

- `id`

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_DailyUserSpend_api_key_idx | api_key | NO |
| LiteLLM_DailyUserSpend_date_idx | date | NO |
| LiteLLM_DailyUserSpend_model_idx | model | NO |
| LiteLLM_DailyUserSpend_pkey | id | YES |
| LiteLLM_DailyUserSpend_user_id_date_api_key_model_custom_ll_key | user_id, date, api_key, model, custom_llm_provider | YES |
| LiteLLM_DailyUserSpend_user_id_idx | user_id | NO |

---

### LiteLLM_EndUserTable

**Row Count:** 1

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| user_id | text | NO | None |  |
| alias | text | YES | None |  |
| spend | double precision(53) | NO | 0.0 | 53 |
| allowed_model_region | text | YES | None |  |
| default_model | text | YES | None |  |
| budget_id | text | YES | None |  |
| blocked | boolean | NO | false |  |

#### Primary Keys

- `user_id`

#### Foreign Keys

| Column | References |
|--------|------------|
| budget_id | LiteLLM_BudgetTable.budget_id |

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_EndUserTable_pkey | user_id | YES |

---

### LiteLLM_ErrorLogs

**Row Count:** 0

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| request_id | text | NO | None |  |
| startTime | timestamp without time zone | NO | None |  |
| endTime | timestamp without time zone | NO | None |  |
| api_base | text | NO | ''::text |  |
| model_group | text | NO | ''::text |  |
| litellm_model_name | text | NO | ''::text |  |
| model_id | text | NO | ''::text |  |
| request_kwargs | jsonb | NO | '{}'::jsonb |  |
| exception_type | text | NO | ''::text |  |
| exception_string | text | NO | ''::text |  |
| status_code | text | NO | ''::text |  |

#### Primary Keys

- `request_id`

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_ErrorLogs_pkey | request_id | YES |

---

### LiteLLM_InvitationLink

**Row Count:** 27

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| id | text | NO | None |  |
| user_id | text | NO | None |  |
| is_accepted | boolean | NO | false |  |
| accepted_at | timestamp without time zone | YES | None |  |
| expires_at | timestamp without time zone | NO | None |  |
| created_at | timestamp without time zone | NO | None |  |
| created_by | text | NO | None |  |
| updated_at | timestamp without time zone | NO | None |  |
| updated_by | text | NO | None |  |

#### Primary Keys

- `id`

#### Foreign Keys

| Column | References |
|--------|------------|
| user_id | LiteLLM_UserTable.user_id |
| created_by | LiteLLM_UserTable.user_id |
| updated_by | LiteLLM_UserTable.user_id |

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_InvitationLink_pkey | id | YES |

---

### LiteLLM_ManagedFileTable

**Row Count:** 0

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| id | text | NO | None |  |
| unified_file_id | text | NO | None |  |
| file_object | jsonb | NO | None |  |
| model_mappings | jsonb | NO | None |  |
| created_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| updated_at | timestamp without time zone | NO | None |  |

#### Primary Keys

- `id`

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_ManagedFileTable_pkey | id | YES |
| LiteLLM_ManagedFileTable_unified_file_id_idx | unified_file_id | NO |
| LiteLLM_ManagedFileTable_unified_file_id_key | unified_file_id | YES |

---

### LiteLLM_ManagedVectorStoresTable

**Row Count:** 0

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| vector_store_id | text | NO | None |  |
| custom_llm_provider | text | NO | None |  |
| vector_store_name | text | YES | None |  |
| vector_store_description | text | YES | None |  |
| vector_store_metadata | jsonb | YES | None |  |
| created_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| updated_at | timestamp without time zone | NO | None |  |
| litellm_credential_name | text | YES | None |  |

#### Primary Keys

- `vector_store_id`

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_ManagedVectorStoresTable_pkey | vector_store_id | YES |

---

### LiteLLM_ModelTable

**Row Count:** 4

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| id | integer(32) | NO | nextval('"LiteLLM_ModelTabl... | 32 |
| aliases | jsonb | YES | None |  |
| created_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| created_by | text | NO | None |  |
| updated_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| updated_by | text | NO | None |  |

#### Primary Keys

- `id`

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_ModelTable_pkey | id | YES |

---

### LiteLLM_OrganizationMembership

**Row Count:** 0

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| user_id | text | NO | None |  |
| organization_id | text | NO | None |  |
| user_role | text | YES | None |  |
| spend | double precision(53) | YES | 0.0 | 53 |
| budget_id | text | YES | None |  |
| created_at | timestamp without time zone | YES | CURRENT_TIMESTAMP |  |
| updated_at | timestamp without time zone | YES | CURRENT_TIMESTAMP |  |

#### Primary Keys

- `user_id`
- `organization_id`

#### Foreign Keys

| Column | References |
|--------|------------|
| user_id | LiteLLM_UserTable.user_id |
| organization_id | LiteLLM_OrganizationTable.organization_id |
| budget_id | LiteLLM_BudgetTable.budget_id |

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_OrganizationMembership_pkey | user_id, organization_id | YES |
| LiteLLM_OrganizationMembership_user_id_organization_id_key | user_id, organization_id | YES |

---

### LiteLLM_OrganizationTable

**Row Count:** 4

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| organization_id | text | NO | None |  |
| organization_alias | text | NO | None |  |
| budget_id | text | NO | None |  |
| metadata | jsonb | NO | '{}'::jsonb |  |
| models | ARRAY | YES | None |  |
| spend | double precision(53) | NO | 0.0 | 53 |
| model_spend | jsonb | NO | '{}'::jsonb |  |
| created_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| created_by | text | NO | None |  |
| updated_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| updated_by | text | NO | None |  |

#### Primary Keys

- `organization_id`

#### Foreign Keys

| Column | References |
|--------|------------|
| budget_id | LiteLLM_BudgetTable.budget_id |

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_OrganizationTable_pkey | organization_id | YES |

---

### LiteLLM_ProxyModelTable

**Row Count:** 0

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| model_id | text | NO | None |  |
| model_name | text | NO | None |  |
| litellm_params | jsonb | NO | None |  |
| model_info | jsonb | YES | None |  |
| created_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| created_by | text | NO | None |  |
| updated_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| updated_by | text | NO | None |  |

#### Primary Keys

- `model_id`

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_ProxyModelTable_pkey | model_id | YES |

---

### LiteLLM_SpendLogs

**Row Count:** 25

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| request_id | text | NO | None |  |
| call_type | text | NO | None |  |
| api_key | text | NO | ''::text |  |
| spend | double precision(53) | NO | 0.0 | 53 |
| total_tokens | integer(32) | NO | 0 | 32 |
| prompt_tokens | integer(32) | NO | 0 | 32 |
| completion_tokens | integer(32) | NO | 0 | 32 |
| startTime | timestamp without time zone | NO | None |  |
| endTime | timestamp without time zone | NO | None |  |
| completionStartTime | timestamp without time zone | YES | None |  |
| model | text | NO | ''::text |  |
| model_id | text | YES | ''::text |  |
| model_group | text | YES | ''::text |  |
| custom_llm_provider | text | YES | ''::text |  |
| api_base | text | YES | ''::text |  |
| user | text | YES | ''::text |  |
| metadata | jsonb | YES | '{}'::jsonb |  |
| cache_hit | text | YES | ''::text |  |
| cache_key | text | YES | ''::text |  |
| request_tags | jsonb | YES | '[]'::jsonb |  |
| team_id | text | YES | None |  |
| end_user | text | YES | None |  |
| requester_ip_address | text | YES | None |  |
| messages | jsonb | YES | '{}'::jsonb |  |
| response | jsonb | YES | '{}'::jsonb |  |
| proxy_server_request | jsonb | YES | '{}'::jsonb |  |
| session_id | text | YES | None |  |

#### Primary Keys

- `request_id`

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_SpendLogs_end_user_idx | end_user | NO |
| LiteLLM_SpendLogs_pkey | request_id | YES |
| LiteLLM_SpendLogs_startTime_idx | startTime | NO |

---

### LiteLLM_TeamMembership

**Row Count:** 0

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| user_id | text | NO | None |  |
| team_id | text | NO | None |  |
| spend | double precision(53) | NO | 0.0 | 53 |
| budget_id | text | YES | None |  |

#### Primary Keys

- `user_id`
- `team_id`

#### Foreign Keys

| Column | References |
|--------|------------|
| budget_id | LiteLLM_BudgetTable.budget_id |

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_TeamMembership_pkey | user_id, team_id | YES |

---

### LiteLLM_TeamTable

**Row Count:** 4

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| team_id | text | NO | None |  |
| team_alias | text | YES | None |  |
| organization_id | text | YES | None |  |
| admins | ARRAY | YES | None |  |
| members | ARRAY | YES | None |  |
| members_with_roles | jsonb | NO | '{}'::jsonb |  |
| metadata | jsonb | NO | '{}'::jsonb |  |
| max_budget | double precision(53) | YES | None | 53 |
| spend | double precision(53) | NO | 0.0 | 53 |
| models | ARRAY | YES | None |  |
| max_parallel_requests | integer(32) | YES | None | 32 |
| tpm_limit | bigint(64) | YES | None | 64 |
| rpm_limit | bigint(64) | YES | None | 64 |
| budget_duration | text | YES | None |  |
| budget_reset_at | timestamp without time zone | YES | None |  |
| blocked | boolean | NO | false |  |
| created_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| updated_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |  |
| model_spend | jsonb | NO | '{}'::jsonb |  |
| model_max_budget | jsonb | NO | '{}'::jsonb |  |
| model_id | integer(32) | YES | None | 32 |
| team_member_permissions | ARRAY | YES | ARRAY[]::text[] |  |

#### Primary Keys

- `team_id`

#### Foreign Keys

| Column | References |
|--------|------------|
| organization_id | LiteLLM_OrganizationTable.organization_id |
| model_id | LiteLLM_ModelTable.id |

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_TeamTable_model_id_key | model_id | YES |
| LiteLLM_TeamTable_pkey | team_id | YES |

---

### LiteLLM_UserNotifications

**Row Count:** 0

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| request_id | text | NO | None |  |
| user_id | text | NO | None |  |
| models | ARRAY | YES | None |  |
| justification | text | NO | None |  |
| status | text | NO | None |  |

#### Primary Keys

- `request_id`

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_UserNotifications_pkey | request_id | YES |

---

### LiteLLM_UserTable

**Row Count:** 37

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| user_id | text | NO | None |  |
| user_alias | text | YES | None |  |
| team_id | text | YES | None |  |
| sso_user_id | text | YES | None |  |
| organization_id | text | YES | None |  |
| password | text | YES | None |  |
| teams | ARRAY | YES | ARRAY[]::text[] |  |
| user_role | text | YES | None |  |
| max_budget | double precision(53) | YES | None | 53 |
| spend | double precision(53) | NO | 0.0 | 53 |
| user_email | text | YES | None |  |
| models | ARRAY | YES | None |  |
| metadata | jsonb | NO | '{}'::jsonb |  |
| max_parallel_requests | integer(32) | YES | None | 32 |
| tpm_limit | bigint(64) | YES | None | 64 |
| rpm_limit | bigint(64) | YES | None | 64 |
| budget_duration | text | YES | None |  |
| budget_reset_at | timestamp without time zone | YES | None |  |
| allowed_cache_controls | ARRAY | YES | ARRAY[]::text[] |  |
| model_spend | jsonb | NO | '{}'::jsonb |  |
| model_max_budget | jsonb | NO | '{}'::jsonb |  |
| created_at | timestamp without time zone | YES | CURRENT_TIMESTAMP |  |
| updated_at | timestamp without time zone | YES | CURRENT_TIMESTAMP |  |

#### Primary Keys

- `user_id`

#### Foreign Keys

| Column | References |
|--------|------------|
| organization_id | LiteLLM_OrganizationTable.organization_id |

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_UserTable_pkey | user_id | YES |
| LiteLLM_UserTable_sso_user_id_key | sso_user_id | YES |

---

### LiteLLM_VerificationToken

**Row Count:** 180

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| token | text | NO | None |  |
| key_name | text | YES | None |  |
| key_alias | text | YES | None |  |
| soft_budget_cooldown | boolean | NO | false |  |
| spend | double precision(53) | NO | 0.0 | 53 |
| expires | timestamp without time zone | YES | None |  |
| models | ARRAY | YES | None |  |
| aliases | jsonb | NO | '{}'::jsonb |  |
| config | jsonb | NO | '{}'::jsonb |  |
| user_id | text | YES | None |  |
| team_id | text | YES | None |  |
| permissions | jsonb | NO | '{}'::jsonb |  |
| max_parallel_requests | integer(32) | YES | None | 32 |
| metadata | jsonb | NO | '{}'::jsonb |  |
| blocked | boolean | YES | None |  |
| tpm_limit | bigint(64) | YES | None | 64 |
| rpm_limit | bigint(64) | YES | None | 64 |
| max_budget | double precision(53) | YES | None | 53 |
| budget_duration | text | YES | None |  |
| budget_reset_at | timestamp without time zone | YES | None |  |
| allowed_cache_controls | ARRAY | YES | ARRAY[]::text[] |  |
| model_spend | jsonb | NO | '{}'::jsonb |  |
| model_max_budget | jsonb | NO | '{}'::jsonb |  |
| budget_id | text | YES | None |  |
| organization_id | text | YES | None |  |
| created_at | timestamp without time zone | YES | CURRENT_TIMESTAMP |  |
| created_by | text | YES | None |  |
| updated_at | timestamp without time zone | YES | CURRENT_TIMESTAMP |  |
| updated_by | text | YES | None |  |
| allowed_routes | ARRAY | YES | ARRAY[]::text[] |  |

#### Primary Keys

- `token`

#### Foreign Keys

| Column | References |
|--------|------------|
| budget_id | LiteLLM_BudgetTable.budget_id |
| organization_id | LiteLLM_OrganizationTable.organization_id |

#### Indexes

| Index Name | Columns | Unique |
|------------|---------|--------|
| LiteLLM_VerificationToken_pkey | token | YES |

---

### LiteLLM_VerificationTokenView

**Row Count:** 180

#### Columns

| Column | Type | Nullable | Default | Length/Precision |
|--------|------|----------|---------|------------------|
| token | text | YES | None |  |
| key_name | text | YES | None |  |
| key_alias | text | YES | None |  |
| soft_budget_cooldown | boolean | YES | None |  |
| spend | double precision(53) | YES | None | 53 |
| expires | timestamp without time zone | YES | None |  |
| models | ARRAY | YES | None |  |
| aliases | jsonb | YES | None |  |
| config | jsonb | YES | None |  |
| user_id | text | YES | None |  |
| team_id | text | YES | None |  |
| permissions | jsonb | YES | None |  |
| max_parallel_requests | integer(32) | YES | None | 32 |
| metadata | jsonb | YES | None |  |
| blocked | boolean | YES | None |  |
| tpm_limit | bigint(64) | YES | None | 64 |
| rpm_limit | bigint(64) | YES | None | 64 |
| max_budget | double precision(53) | YES | None | 53 |
| budget_duration | text | YES | None |  |
| budget_reset_at | timestamp without time zone | YES | None |  |
| allowed_cache_controls | ARRAY | YES | None |  |
| model_spend | jsonb | YES | None |  |
| model_max_budget | jsonb | YES | None |  |
| budget_id | text | YES | None |  |
| organization_id | text | YES | None |  |
| created_at | timestamp without time zone | YES | None |  |
| created_by | text | YES | None |  |
| updated_at | timestamp without time zone | YES | None |  |
| updated_by | text | YES | None |  |
| team_spend | double precision(53) | YES | None | 53 |
| team_max_budget | double precision(53) | YES | None | 53 |
| team_tpm_limit | bigint(64) | YES | None | 64 |
| team_rpm_limit | bigint(64) | YES | None | 64 |

---

## Entity Relationship Diagram

```mermaid
erDiagram
    LiteLLM_AuditLog {
        text id PK
        timestamp without time zone updated_at
        text changed_by
        text changed_by_api_key
        text action
        text table_name
        text object_id
        jsonb before_value
        jsonb updated_values
    }

    LiteLLM_BudgetTable {
        text budget_id PK
        double precision max_budget
        double precision soft_budget
        integer max_parallel_requests
        bigint tpm_limit
        bigint rpm_limit
        jsonb model_max_budget
        text budget_duration
        timestamp without time zone budget_reset_at
        timestamp without time zone created_at
        text created_by
        timestamp without time zone updated_at
        text updated_by
    }

    LiteLLM_Config {
        text param_name PK
        jsonb param_value
    }

    LiteLLM_CredentialsTable {
        text credential_id PK
        text credential_name
        jsonb credential_values
        jsonb credential_info
        timestamp without time zone created_at
        text created_by
        timestamp without time zone updated_at
        text updated_by
    }

    LiteLLM_CronJob {
        text cronjob_id PK
        text pod_id
        USER-DEFINED status
        timestamp without time zone last_updated
        timestamp without time zone ttl
    }

    LiteLLM_DailyTagSpend {
        text id PK
        text tag
        text date
        text api_key
        text model
        text model_group
        text custom_llm_provider
        integer prompt_tokens
        integer completion_tokens
        integer cache_read_input_tokens
        integer cache_creation_input_tokens
        double precision spend
        integer api_requests
        integer successful_requests
        integer failed_requests
        timestamp without time zone created_at
        timestamp without time zone updated_at
    }

    LiteLLM_DailyTeamSpend {
        text id PK
        text team_id
        text date
        text api_key
        text model
        text model_group
        text custom_llm_provider
        integer prompt_tokens
        integer completion_tokens
        double precision spend
        integer api_requests
        integer successful_requests
        integer failed_requests
        timestamp without time zone created_at
        timestamp without time zone updated_at
        integer cache_creation_input_tokens
        integer cache_read_input_tokens
    }

    LiteLLM_DailyUserSpend {
        text id PK
        text user_id
        text date
        text api_key
        text model
        text model_group
        text custom_llm_provider
        integer prompt_tokens
        integer completion_tokens
        double precision spend
        timestamp without time zone created_at
        timestamp without time zone updated_at
        integer api_requests
        integer failed_requests
        integer successful_requests
        integer cache_creation_input_tokens
        integer cache_read_input_tokens
    }

    LiteLLM_EndUserTable {
        text user_id PK
        text alias
        double precision spend
        text allowed_model_region
        text default_model
        text budget_id
        boolean blocked
    }

    LiteLLM_ErrorLogs {
        text request_id PK
        timestamp without time zone startTime
        timestamp without time zone endTime
        text api_base
        text model_group
        text litellm_model_name
        text model_id
        jsonb request_kwargs
        text exception_type
        text exception_string
        text status_code
    }

    LiteLLM_InvitationLink {
        text id PK
        text user_id
        boolean is_accepted
        timestamp without time zone accepted_at
        timestamp without time zone expires_at
        timestamp without time zone created_at
        text created_by
        timestamp without time zone updated_at
        text updated_by
    }

    LiteLLM_ManagedFileTable {
        text id PK
        text unified_file_id
        jsonb file_object
        jsonb model_mappings
        timestamp without time zone created_at
        timestamp without time zone updated_at
    }

    LiteLLM_ManagedVectorStoresTable {
        text vector_store_id PK
        text custom_llm_provider
        text vector_store_name
        text vector_store_description
        jsonb vector_store_metadata
        timestamp without time zone created_at
        timestamp without time zone updated_at
        text litellm_credential_name
    }

    LiteLLM_ModelTable {
        integer id PK
        jsonb aliases
        timestamp without time zone created_at
        text created_by
        timestamp without time zone updated_at
        text updated_by
    }

    LiteLLM_OrganizationMembership {
        text user_id PK
        text organization_id PK
        text user_role
        double precision spend
        text budget_id
        timestamp without time zone created_at
        timestamp without time zone updated_at
    }

    LiteLLM_OrganizationTable {
        text organization_id PK
        text organization_alias
        text budget_id
        jsonb metadata
        ARRAY models
        double precision spend
        jsonb model_spend
        timestamp without time zone created_at
        text created_by
        timestamp without time zone updated_at
        text updated_by
    }

    LiteLLM_ProxyModelTable {
        text model_id PK
        text model_name
        jsonb litellm_params
        jsonb model_info
        timestamp without time zone created_at
        text created_by
        timestamp without time zone updated_at
        text updated_by
    }

    LiteLLM_SpendLogs {
        text request_id PK
        text call_type
        text api_key
        double precision spend
        integer total_tokens
        integer prompt_tokens
        integer completion_tokens
        timestamp without time zone startTime
        timestamp without time zone endTime
        timestamp without time zone completionStartTime
        text model
        text model_id
        text model_group
        text custom_llm_provider
        text api_base
        text user
        jsonb metadata
        text cache_hit
        text cache_key
        jsonb request_tags
        text team_id
        text end_user
        text requester_ip_address
        jsonb messages
        jsonb response
        jsonb proxy_server_request
        text session_id
    }

    LiteLLM_TeamMembership {
        text user_id PK
        text team_id PK
        double precision spend
        text budget_id
    }

    LiteLLM_TeamTable {
        text team_id PK
        text team_alias
        text organization_id
        ARRAY admins
        ARRAY members
        jsonb members_with_roles
        jsonb metadata
        double precision max_budget
        double precision spend
        ARRAY models
        integer max_parallel_requests
        bigint tpm_limit
        bigint rpm_limit
        text budget_duration
        timestamp without time zone budget_reset_at
        boolean blocked
        timestamp without time zone created_at
        timestamp without time zone updated_at
        jsonb model_spend
        jsonb model_max_budget
        integer model_id
        ARRAY team_member_permissions
    }

    LiteLLM_UserNotifications {
        text request_id PK
        text user_id
        ARRAY models
        text justification
        text status
    }

    LiteLLM_UserTable {
        text user_id PK
        text user_alias
        text team_id
        text sso_user_id
        text organization_id
        text password
        ARRAY teams
        text user_role
        double precision max_budget
        double precision spend
        text user_email
        ARRAY models
        jsonb metadata
        integer max_parallel_requests
        bigint tpm_limit
        bigint rpm_limit
        text budget_duration
        timestamp without time zone budget_reset_at
        ARRAY allowed_cache_controls
        jsonb model_spend
        jsonb model_max_budget
        timestamp without time zone created_at
        timestamp without time zone updated_at
    }

    LiteLLM_VerificationToken {
        text token PK
        text key_name
        text key_alias
        boolean soft_budget_cooldown
        double precision spend
        timestamp without time zone expires
        ARRAY models
        jsonb aliases
        jsonb config
        text user_id
        text team_id
        jsonb permissions
        integer max_parallel_requests
        jsonb metadata
        boolean blocked
        bigint tpm_limit
        bigint rpm_limit
        double precision max_budget
        text budget_duration
        timestamp without time zone budget_reset_at
        ARRAY allowed_cache_controls
        jsonb model_spend
        jsonb model_max_budget
        text budget_id
        text organization_id
        timestamp without time zone created_at
        text created_by
        timestamp without time zone updated_at
        text updated_by
        ARRAY allowed_routes
    }

    LiteLLM_VerificationTokenView {
        text token
        text key_name
        text key_alias
        boolean soft_budget_cooldown
        double precision spend
        timestamp without time zone expires
        ARRAY models
        jsonb aliases
        jsonb config
        text user_id
        text team_id
        jsonb permissions
        integer max_parallel_requests
        jsonb metadata
        boolean blocked
        bigint tpm_limit
        bigint rpm_limit
        double precision max_budget
        text budget_duration
        timestamp without time zone budget_reset_at
        ARRAY allowed_cache_controls
        jsonb model_spend
        jsonb model_max_budget
        text budget_id
        text organization_id
        timestamp without time zone created_at
        text created_by
        timestamp without time zone updated_at
        text updated_by
        double precision team_spend
        double precision team_max_budget
        bigint team_tpm_limit
        bigint team_rpm_limit
    }

    LiteLLM_EndUserTable ||--o| LiteLLM_BudgetTable : budget_id
    LiteLLM_InvitationLink ||--o| LiteLLM_UserTable : user_id
    LiteLLM_InvitationLink ||--o| LiteLLM_UserTable : created_by
    LiteLLM_InvitationLink ||--o| LiteLLM_UserTable : updated_by
    LiteLLM_OrganizationMembership ||--o| LiteLLM_UserTable : user_id
    LiteLLM_OrganizationMembership ||--o| LiteLLM_OrganizationTable : organization_id
    LiteLLM_OrganizationMembership ||--o| LiteLLM_BudgetTable : budget_id
    LiteLLM_OrganizationTable ||--o| LiteLLM_BudgetTable : budget_id
    LiteLLM_TeamMembership ||--o| LiteLLM_BudgetTable : budget_id
    LiteLLM_TeamTable ||--o| LiteLLM_OrganizationTable : organization_id
    LiteLLM_TeamTable ||--o| LiteLLM_ModelTable : model_id
    LiteLLM_UserTable ||--o| LiteLLM_OrganizationTable : organization_id
    LiteLLM_VerificationToken ||--o| LiteLLM_BudgetTable : budget_id
    LiteLLM_VerificationToken ||--o| LiteLLM_OrganizationTable : organization_id
```

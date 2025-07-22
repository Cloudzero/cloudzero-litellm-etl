# CloudZero Resource Names (CZRN) Implementation for LiteLLM

This document describes how CloudZero Resource Names (CZRNs) are implemented in the LiteLLM to CloudZero ETL tool.

## CZRN Format

CZRNs follow the standard CloudZero format:

```
czrn:<service-type>:<provider>:<region>:<owner-account-id>:<resource-type>:<cloud-local-id>
```

## LiteLLM CZRN Mapping

For LiteLLM resources, we map the components as follows:

### Service Type
Always `litellm` (the service managing the LLM calls)

### Provider
The `custom_llm_provider` field from LiteLLM daily spend data, normalized to standard provider names:
- `openai` → `openai`
- `anthropic` → `anthropic`
- `azure`, `azure-ai` → `azure`
- `aws`, `aws-bedrock` → `aws`
- `gcp`, `google` → `gcp`
- `cohere` → `cohere`
- `huggingface` → `huggingface`
- `replicate` → `replicate`
- `together-ai` → `together-ai`
- Unknown providers → normalized version of provider name

### Region
Always `cross-region` (LiteLLM operates across multiple regions and abstracts away the underlying provider regions)

### Owner Account ID
The `entity_id` field from LiteLLM data (team_id or user_id), normalized to meet CZRN requirements:
- Converted to lowercase
- Invalid characters replaced with hyphens
- Consecutive hyphens removed
- Leading/trailing hyphens stripped
- Empty values become `unknown`

### Resource Type
Always `llm-usage` (represents LLM usage/inference operations)

### Cloud Local ID
The `model` field from LiteLLM data (e.g., `gpt-4`, `claude-3-5-sonnet`, `gpt-4-turbo`)

## Example CZRNs

### User Usage
```
czrn:litellm:openai:cross-region:john-doe:llm-usage:gpt-4
```

### Team Usage
```
czrn:litellm:anthropic:cross-region:engineering-team:llm-usage:claude-3-5-sonnet
```

### Azure Provider
```
czrn:litellm:azure:cross-region:jane-smith:llm-usage:gpt-4-turbo
```

### Unknown Entity
```
czrn:litellm:openai:cross-region:unknown:llm-usage:gpt-3-5-turbo
```

## CZRN Component Normalization

### Provider Normalization
Providers are normalized using a mapping table and character replacement:
1. Convert to lowercase
2. Replace underscores with hyphens
3. Apply provider mapping (e.g., `azure-ai` → `azure`)
4. Fall back to normalized version if not in mapping

### Owner Account ID Normalization  
Entity IDs are normalized for CZRN compatibility:
1. Convert to lowercase (unless uppercase allowed)
2. Replace invalid characters (non-alphanumeric, non-hyphen) with hyphens
3. Remove consecutive hyphens
4. Strip leading/trailing hyphens
5. Use `unknown` if result is empty

## CBF Integration

CZRNs are integrated into CloudZero CBF (Common Billing Format) records as follows:

### Resource ID
The complete CZRN is used as the `resource/id` field in CBF records.

### CBF Field Mapping
CZRN components map to specific CBF fields:
- `resource/service` ← CZRN service-type (`litellm`)
- `resource/account` ← CZRN owner-account-id (normalized entity_id)
- `resource/region` ← CZRN region (`cross-region`) 
- `resource/usage_family` ← CZRN resource-type (`llm-usage`)

### Resource Tags
Additional CZRN components are added as resource tags:
- `resource/tag:provider` ← CZRN provider component
- `resource/tag:model` ← CZRN cloud-local-id component (model)

## CZRN Analysis

Use the built-in analysis command to examine CZRN generation:

```bash
# Analyze CZRN generation for your data
ll2cz analyze czrn --limit 1000

# Check for unknown-account issues
ll2cz analyze czrn --limit 10000
```

The analysis shows:
- CZRN component breakdown (providers, models, accounts)
- Generated CZRNs with their components
- Records that generate unknown-account CZRNs
- Error details for failed CZRN generation

## Benefits

1. **Consistent Identification**: Same resources generate the same CZRN across multiple runs
2. **CloudZero Compatible**: Follows CloudZero CZRN standards for seamless integration
3. **Cross-Provider**: Works consistently across all LLM providers  
4. **Granular Tracking**: Enables cost attribution at the entity + model level
5. **Normalized Data**: Handles messy entity IDs through normalization rules
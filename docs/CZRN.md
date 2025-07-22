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
- `azure_ai` → `azure`
- `aws_bedrock` → `aws`
- `together_ai` → `together-ai`
- Unknown providers → `unknown`

### Region
Always `cross-region` (LiteLLM operates across multiple regions and abstracts away the underlying provider regions)

### Owner Account ID
A privacy-preserving SHA-256 hash of the API key in the format `key-<12-hex-chars>`. This ensures:
- Consistent identification of the same API key across records
- Privacy protection by not exposing the actual API key
- Deterministic resource identification for cost attribution

### Resource Type
Always `llm-usage` (represents LLM usage/inference operations)

### Cloud Local ID
A pipe-separated identifier combining:
- `entity_type` (user/team)
- `entity_id` (the specific user or team identifier)
- `model` (the AI model used)

Format: `{entity_type}|{entity_id}|{model}`

## Example CZRNs

### User Usage
```
czrn:litellm:openai:cross-region:key-abc123def456:llm-usage:user|john_doe|gpt-4
```

### Team Usage
```
czrn:litellm:anthropic:cross-region:key-def789abc123:llm-usage:team|engineering|claude-3-5-sonnet
```

### Azure Provider
```
czrn:litellm:azure:cross-region:key-789def456abc:llm-usage:user|jane_smith|gpt-4-turbo
```

## Benefits

1. **Consistent Identification**: Same resources generate the same CZRN across multiple runs
2. **Privacy-Preserving**: API keys are hashed for security
3. **CloudZero Compatible**: Follows CloudZero CZRN standards for seamless integration
4. **Cross-Provider**: Works consistently across all LLM providers
5. **Granular Tracking**: Enables cost attribution at the user/team + model + date level

## Usage in CBF Records

CZRNs are used as the `resource_id` field in CloudZero CBF (Common Billing Format) records, enabling CloudZero to properly identify and attribute costs to specific resources in their cost management platform.
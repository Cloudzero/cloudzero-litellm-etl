# CloudZero Common Bill Format (CBF) Reference

## Overview

CloudZero's Common Bill Format (CBF) is a standardized schema for ingesting cost and usage data into CloudZero. This document provides a comprehensive reference of all supported CBF columns based on the [official CloudZero documentation](https://docs.cloudzero.com/docs/anycost-common-bill-format-cbf).

## Important Notes

- **Column Restrictions**: CBF only supports the columns listed below. No custom columns can be added outside of `resource/tag:<key>` format.
- **Required Fields**: Some fields are required depending on the context (e.g., `resource/id` is required when resource tags are present).
- **Field Naming**: Column names must match exactly as specified (case-sensitive).

## Supported CBF Columns

### Line Item Columns
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `lineitem/id` | String | No | Uniquely identifies specific line item |
| `lineitem/type` | String | No | Categorizes line item type (Usage, Tax, Discount, etc.) |
| `lineitem/description` | String | No | Optional description of line item |

### Time Columns
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `time/usage_start` | ISO DateTime | **Yes** | ISO datetime when usage begins |
| `time/usage_end` | ISO DateTime | No | End of usage timespan |

### Resource Columns
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `resource/id` | String | **Yes*** | Required if resource tags are used |
| `resource/service` | String | No | Cloud service category |
| `resource/account` | String | No | Account/project for resource |
| `resource/region` | String | No | Geographic region of resource |
| `resource/usage_family` | String | No | Subdivision of resource service |
| `resource/tag:<key>` | String | No | Custom resource attributes (flexible key names) |

### Action Columns
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `action/operation` | String | No | Action performed |
| `action/usage_type` | String | No | Subdivision of operation |
| `action/region` | String | No | Region of operation |
| `action/account` | String | No | Account of operation |

### Usage Columns
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `usage/amount` | Numeric | No | Numeric value of usage |
| `usage/units` | String | No | Description of usage units |

### Cost Columns
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `cost/cost` | Numeric | **Yes** | Billed cost |
| `cost/discounted_cost` | Numeric | No | Net cost after discounts |
| `cost/amortized_cost` | Numeric | No | Effective cost with committed use |
| `cost/discounted_amortized_cost` | Numeric | No | Net effective cost |
| `cost/on_demand_cost` | Numeric | No | Hypothetical full-price cost |

### Bill Columns
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `bill/invoice_id` | String | No | Unique bill identifier |

### Kubernetes Columns
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `k8s/cluster` | String | No | Kubernetes cluster |
| `k8s/namespace` | String | No | Kubernetes namespace |
| `k8s/deployment` | String | No | Kubernetes deployment |
| `k8s/labels` | String | No | Kubernetes resource labels |

## LiteLLM to CBF Mapping

For our LiteLLM ETL pipeline, we use the following CBF mapping:

### Core Fields
- `time/usage_start` ← Daily usage date
- `cost/cost` ← LiteLLM spend amount
- `resource/id` ← Generated CZRN
- `usage/amount` ← Total token count
- `usage/units` ← "tokens"
- `lineitem/type` ← "Usage"

### CZRN Component Mapping
- `resource/service` ← CZRN service-type ("litellm")
- `resource/account` ← CZRN owner-account-id (entity_id)
- `resource/region` ← CZRN region ("cross-region")
- `resource/usage_family` ← CZRN resource (extracted model name)

### Resource Tags (LiteLLM Specific)
- `resource/tag:provider` ← CZRN provider (openai, anthropic, etc.)
- `resource/tag:model` ← CZRN cloud-local-id (full model identifier)
- `resource/tag:entity_type` ← "user" or "team"
- `resource/tag:entity_id` ← Specific user/team identifier
- `resource/tag:model_group` ← LiteLLM model group
- `resource/tag:api_key` ← Full API key used
- `resource/tag:api_requests` ← Total API requests
- `resource/tag:successful_requests` ← Successful requests count
- `resource/tag:failed_requests` ← Failed requests count
- `resource/tag:prompt_tokens` ← Input token count
- `resource/tag:completion_tokens` ← Output token count
- `resource/tag:total_tokens` ← Combined token count
- `resource/tag:cache_creation_tokens` ← Cache creation tokens
- `resource/tag:cache_read_tokens` ← Cache read tokens

## Best Practices

1. **Use Standard Fields First**: Always prefer standard CBF columns over resource tags when possible.
2. **Consistent Naming**: Use consistent naming conventions for resource tags across your data.
3. **Required Fields**: Always include required fields (`time/usage_start`, `cost/cost`, and `resource/id` when using tags).
4. **Data Types**: Ensure numeric fields contain proper numeric values, not strings.
5. **ISO Dates**: Use ISO 8601 format for datetime fields.

## Validation

Before ingesting CBF data:
- Verify all column names match the supported list exactly
- Confirm required fields are present
- Validate data types (especially dates and numbers)
- Check that `resource/id` is present when using resource tags

## References

- [CloudZero CBF Documentation](https://docs.cloudzero.com/docs/anycost-common-bill-format-cbf)
- [CloudZero Resource Names (CZRN) Documentation](./CZRN.md)
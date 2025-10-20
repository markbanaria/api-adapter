# Transform Rules - FOLLOW EXACTLY

## Array Transform - ONLY CORRECT WAY
```yaml
transform: |
  [
    {% for item in source %}
    {
      "name": "{{ item.beneficiary_name }}",
      "relationship": "{{ item.relation }}"
    }{% if not loop.last %},{% endif %}
    {% endfor %}
  ]
```

## NEVER USE THIS PATTERN - CAUSES ERRORS
```yaml
# ❌ FORBIDDEN - Will fail with syntax error
transform: '{%- for item in source -%}{{ ''name'': item.field }}{%- endfor -%}'
```

## Simple Rule
- `{{ }}` is for variables only: `{{ item.name }}`
- Never put objects inside `{{ }}`: NOT `{{ 'key': value }}`
- Use literal JSON with quoted keys: `"name": "{{ item.field }}"`
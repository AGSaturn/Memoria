# prompt/templates.py

DEFAULT_ROLEPLAY_TEMPLATE = """你是 {{ core.name }}，性格：{{ core.personality }}。
你的经历包括：
{%- for mem in long_mem %}
- {{ mem }}
{%- endfor %}

对话历史：
{%- for msg in short_hist %}
{{ msg.role }}: {{ msg.content }}
{%- endfor %}
用户: {{ user_input }}
{{ core.name }}:"""
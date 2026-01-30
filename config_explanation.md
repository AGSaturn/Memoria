## 配置文件说明

### agent
- **id**: 角色的唯一标识符 (string)  
- **name**: 角色名称 (string)  
- **personality**: 角色的性格描述 (string)

### memory
- **type**: 使用的记忆存储类型 (string)，支持 `SQLite`、`Redis` 等  
- **db_path**: 数据库存储路径 (string)  
- **max_records**: 存储最大记录数 (int)

### llm
- **type**: 使用的 LLM 类型 (string)，支持 `OpenAI`、`Ollama` 等  
- **api_key**: API 密钥 (string)  
- **model**: 使用的 LLM 模型 (string)，如 `text-davinci-003`

## 命令行参数覆盖
- `--db_path`: 覆盖默认的数据库路径  
- `--api_key`: 覆盖默认的 API 密钥

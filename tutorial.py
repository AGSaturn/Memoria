# 加载配置
config = load_config("config.json")

# 初始化 MemoryManager（例如使用 SQLite 存储）
memory_config = config["memory"]
if memory_config["type"] == "SQLite":
    memory = SQLiteMemoryManager(db_path=memory_config["db_path"], max_records=memory_config["max_records"])

# 初始化 LLMClient（例如使用 OpenAI）
llm_config = config["llm"]
if llm_config["type"] == "OpenAI":
    llm = OpenAIClient(api_key=llm_config["api_key"], model=llm_config["model"])

# 初始化 Agent
agent_config = config["agent"]
agent = SimpleAgent(agent_config["id"], {"name": agent_config["name"], "personality": agent_config["personality"]}, memory, llm)

# 进行对话
reply = await agent.step("你好，Luna！")
print(reply)

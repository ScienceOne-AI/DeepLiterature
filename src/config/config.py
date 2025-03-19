# encoding: utf-8
import yaml
import os

ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_PATH = os.path.join(ROOT_PATH, 'resources')

with open(os.path.join(ROOT_PATH, 'config/config.yml'),'r', encoding='utf-8') as conf_file:
    config = yaml.safe_load(conf_file)
service_name = "deepliterature"
config = config[service_name]

################# Language Configuration ###########################
LANGUAGE = config["language"]

################# llm Configuration ###########################
LLM_CONFIG = config["llm"]
MAX_CONTEXT_LENGTH = LLM_CONFIG["max_context_length"]
LLM_MODEL =  LLM_CONFIG["llm_model"]

################# remote-llm Configuration ###########################
REMOTE_LLM_CONFIG = LLM_CONFIG["remote-llm"]
REMOTE_LLM_API_URL = REMOTE_LLM_CONFIG["api_url"]
REMOTE_LLM_API_KEY = REMOTE_LLM_CONFIG["api_key"]
REMOTE_LLM_MODEL_NAME = REMOTE_LLM_CONFIG["model_name"]
REMOTE_LLM_TOKENIZER_CONFIG = REMOTE_LLM_CONFIG["tokenizer"]
REMOTE_LLM_TOKENIZER_NAME_OR_PATH = REMOTE_LLM_TOKENIZER_CONFIG.get("tokenizer_name_or_path", "")
REMOTE_LLM_TOKENIZER_CLASS = REMOTE_LLM_TOKENIZER_CONFIG["tokenizer_class"]

################# remote-reasoning-llm Configuration ###########################
REMOTE_REASONING_LLM_CONFIG = LLM_CONFIG["remote-reasoning-llm"]
REMOTE_REASONING_LLM_API_URL = REMOTE_REASONING_LLM_CONFIG["api_url"]
REMOTE_REASONING_LLM_API_KEY = REMOTE_REASONING_LLM_CONFIG["api_key"]
REMOTE_REASONING_LLM_MODEL_NAME = REMOTE_REASONING_LLM_CONFIG["model_name"]
REMOTE_REASONING_LLM_TOKENIZER_CONFIG = REMOTE_REASONING_LLM_CONFIG["tokenizer"]
REMOTE_REASONING_LLM_TOKENIZER_NAME_OR_PATH = os.path.join(RESOURCES_PATH, REMOTE_REASONING_LLM_TOKENIZER_CONFIG.get("tokenizer_name_or_path", ""))
REMOTE_REASONING_LLM_TOKENIZER_CLASS = REMOTE_REASONING_LLM_TOKENIZER_CONFIG["tokenizer_class"]


################# search-engine Configuration ###########################
SEARCH_CONFIG = config["search-engine"]
SEARCH_ENGINE = SEARCH_CONFIG["search_engine"]

################# search-serpapi Configuration ###########################
SERPAPI_CONFIG = SEARCH_CONFIG["serp"]
SERPAPI_URL = SERPAPI_CONFIG["api_url"]
SERPAPI_KEY = SERPAPI_CONFIG["api_key"]
SERPAPI_GL = SERPAPI_CONFIG["gl"]
SERPAPI_HL = SERPAPI_CONFIG["hl"]


################# jina Configuration ###########################
JINA_CONFIG = config["jina"]
JINA_API_URL = JINA_CONFIG["api_url"]
JINA_API_KEY = JINA_CONFIG["api_key"]

################# code-runner Configuration ###########################
CODE_RUNNER_CONFIG = config["code-runner"]
CODE_RUNNER_API_URL = CODE_RUNNER_CONFIG["api_url"]




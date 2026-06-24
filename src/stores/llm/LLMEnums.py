from enum import Enum

class LLMEnums(Enum):
    OPENAI = "OPENAI"
    COHERE = "COHERE"
    VERTEX = "VERTEX"
    DEEPSEEK = "DEEPSEEK"
    BGE = "BGE"

class OpenAIEnums(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class CoHereEnums(Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "CHATBOT"

    DOCUMENT = "search_document"
    QUERY = "search_query"


class VertexAIEnums(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "model"


class DocumentTypeEnum(Enum):
    DOCUMENT = "document"
    QUERY = "query"
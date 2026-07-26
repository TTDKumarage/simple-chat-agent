from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    # Omit, or send null/empty, to have the server generate a new session_id
    # and return it - useful for a first message when the caller doesn't have
    # one yet. Pass it back on every following request to continue that
    # conversation.
    session_id: Optional[str] = Field(default=None, max_length=128)
    message: str = Field(..., min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    session_id: str
    reply: str


class ResetRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)


class ConfigResponse(BaseModel):
    app_name: str
    provider: str
    model: str
    rag_enabled: bool
    streaming: bool


class HealthResponse(BaseModel):
    status: str


class SiteTypeInfo(BaseModel):
    value: str
    label: str


class FrontendConfigResponse(BaseModel):
    type: str
    label: str
    brand: str
    api_base: str
    greeting: str
    use_gateway_key: bool = False
    api_key: str = ""


class FrontendConfigUpdateRequest(BaseModel):
    type: str
    api_base: str = ""
    greeting: str = Field(..., min_length=1, max_length=2000)
    use_gateway_key: bool = False
    api_key: str = ""


class EmbedFileResult(BaseModel):
    filename: str
    chunks: int


class EmbedResponse(BaseModel):
    status: str
    index_name: str
    namespace: str
    files_processed: int
    chunks_embedded: int
    files: list[EmbedFileResult]


class PineconeConnectionRequest(BaseModel):
    pinecone_api_key: str = Field(..., min_length=1)
    pinecone_index_name: str = ""
    pinecone_host: str = ""
    pinecone_namespace: str = ""


class EmbeddedFileInfo(BaseModel):
    filename: str
    chunks: int


class EmbeddedFilesResponse(BaseModel):
    files: list[EmbeddedFileInfo]


class DeleteFileRequest(PineconeConnectionRequest):
    filename: str = Field(..., min_length=1)


class DeleteFileResponse(BaseModel):
    filename: str
    chunks_deleted: int


class KBConfigResponse(BaseModel):
    type: str
    pinecone_api_key: str
    pinecone_index_name: str
    pinecone_host: str
    pinecone_namespace: str
    pinecone_cloud: str
    pinecone_region: str
    pinecone_create_if_missing: bool
    embedding_model: str
    embedding_dimension: int
    embedding_api_key: str


class KBConfigUpdateRequest(BaseModel):
    type: str
    pinecone_api_key: str = ""
    pinecone_index_name: str = ""
    pinecone_host: str = ""
    pinecone_namespace: str = ""
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    pinecone_create_if_missing: bool = True
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    embedding_api_key: str = ""

from typing import Literal

from pydantic import BaseModel, Field


Platform = Literal["feishu", "dingtalk", "whatsapp", "mock"]
ProductStatus = Literal["active", "inactive"]
ConversationStatus = Literal["auto", "needs_human", "human"]
MessageDirection = Literal["inbound", "outbound"]


class ProductImage(BaseModel):
    id: str
    product_id: str
    url: str
    created_at: str


class Product(BaseModel):
    id: str
    title: str
    sku: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: ProductStatus
    external_url: str
    images: list[ProductImage] = Field(default_factory=list)
    created_at: str
    updated_at: str


class ProductCreate(BaseModel):
    title: str
    sku: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: ProductStatus = "active"
    external_url: str


class ProductUpdate(BaseModel):
    title: str | None = None
    sku: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    status: ProductStatus | None = None
    external_url: str | None = None


class Conversation(BaseModel):
    id: str
    platform: Platform
    external_conversation_id: str
    status: ConversationStatus
    created_at: str
    updated_at: str


class MessagePayloadText(BaseModel):
    type: Literal["text"]
    text: str


class MessagePayloadProducts(BaseModel):
    type: Literal["products"]
    product_ids: list[str]
    text: str | None = None


MessagePayload = MessagePayloadText | MessagePayloadProducts


class Message(BaseModel):
    id: str
    conversation_id: str
    direction: MessageDirection
    sender_id: str | None = None
    payload: MessagePayload
    created_at: str


class ConnectorConfig(BaseModel):
    platform: Platform
    enabled: bool = True
    webhook_secret: str | None = None
    access_token: str | None = None
    extra_json: dict[str, object] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    top_n: int = 3
    fallback_text: str = "我暂时没找到完全匹配的商品。你可以补充一下用途/预算/规格吗？"
    force_clarify_when_low_confidence: bool = True
    min_relevance_score: float = 0.35


class Memory(BaseModel):
    user_id: str
    preferences: dict[str, object] = Field(default_factory=dict)
    summary_text: str = ""
    created_at: str
    updated_at: str


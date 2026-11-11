from typing import Literal, Any
from pydantic import BaseModel, Field


class ContractResponse(BaseModel):
    request_id: str = Field(description="Identificador UUID da requisição")
    status: str = Field(description="Status do recebimento")
    message: str = Field(description="Descrição do resultado")
    name_file: str = Field(description="Nome original do arquivo")
    file_type: Literal["PDF", "TXT"] = Field(description="Tipo do arquivo")
    size_bytes: int = Field(description="Tamanho do arquivo recebido")
    data: dict[str, Any] = Field(description="Dados do contrato extraída")
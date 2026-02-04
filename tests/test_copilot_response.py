from copilot import CopilotClient
from copilot.types import SessionConfig
import asyncio

async def test():
    client = CopilotClient()
    session = await client.create_session(SessionConfig())
    
    print("Enviando mensaje...")
    response = await session.send({'prompt': 'Hello, how are you?'})
    
    print(f"\nTipo de respuesta: {type(response)}")
    print(f"Atributos de respuesta: {dir(response)}")
    print(f"\nRespuesta completa: {response}")
    
    if isinstance(response, str):
        print("La respuesta ES un string directamente")
    elif hasattr(response, 'content'):
        print(f"Respuesta tiene .content: {response.content}")
    elif hasattr(response, 'text'):
        print(f"Respuesta tiene .text: {response.text}")
    elif hasattr(response, 'message'):
        print(f"Respuesta tiene .message: {response.message}")

asyncio.run(test())

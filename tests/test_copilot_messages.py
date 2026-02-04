from copilot import CopilotClient
from copilot.types import SessionConfig
import asyncio

async def test():
    client = CopilotClient()
    session = await client.create_session(SessionConfig())
    
    print("=== Probando send_and_wait() ===")
    message_id = await session.send({'prompt': 'What is the capital of France?'})
    print(f"Message ID enviado: {message_id}")
    
    response = await session.send_and_wait({'prompt': 'What is the capital of Spain?'})
    print(f"\nTipo respuesta send_and_wait: {type(response)}")
    print(f"Respuesta: {response}")
    print()
    
    print("=== Probando get_messages() ===")
    messages = await session.get_messages()
    print(f"Tipo: {type(messages)}")
    print(f"Mensajes: {messages}")
    if isinstance(messages, list) and len(messages) > 0:
        print(f"\nPrimer mensaje:")
        print(f"  Tipo: {type(messages[0])}")
        print(f"  Contenido: {messages[0]}")
        if hasattr(messages[0], '__dict__'):
            print(f"  Atributos: {messages[0].__dict__}")

asyncio.run(test())

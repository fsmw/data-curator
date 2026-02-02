from copilot import CopilotClient
from copilot.types import SessionConfig
import asyncio
import json

async def test():
    client = CopilotClient()
    session = await client.create_session(SessionConfig())
    
    print("=== Probando session.send() ===")
    response1 = await session.send({'prompt': 'What is 2+2?'})
    print(f"Tipo: {type(response1)}")
    print(f"Valor: {response1}")
    print()
    
    # Ver si hay otros métodos
    print("=== Métodos de session ===")
    methods = [m for m in dir(session) if not m.startswith('_') and callable(getattr(session, m))]
    print(methods)
    print()
    
    # Probar con message en lugar de prompt
    print("=== Probando con 'message' ===")
    try:
        response2 = await session.send({'message': 'What is 3+3?'})
        print(f"Con message: {response2}")
    except Exception as e:
        print(f"Error con message: {e}")
    print()
    
    # Probar solo con el string
    print("=== Probando con string directo ===")
    try:
        response3 = await session.send('What is 4+4?')
        print(f"Con string: {response3}")
    except Exception as e:
        print(f"Error con string: {e}")

asyncio.run(test())

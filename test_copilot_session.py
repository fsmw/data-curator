from copilot import CopilotClient
from copilot.types import SessionConfig
import asyncio

async def test():
    client = CopilotClient()
    
    # Probar sin parámetros
    try:
        session = await client.create_session()
        print("✓ create_session() sin parámetros funciona")
    except Exception as e:
        print(f"✗ create_session() sin parámetros falló: {e}")
    
    # Probar con SessionConfig vacío
    try:
        session2 = await client.create_session(SessionConfig())
        print("✓ create_session(SessionConfig()) funciona")
    except Exception as e:
        print(f"✗ create_session(SessionConfig()) falló: {e}")
    
    # Probar con session_id
    try:
        session3 = await client.create_session(SessionConfig(session_id="test123"))
        print("✓ create_session con session_id funciona")
    except Exception as e:
        print(f"✗ create_session con session_id falló: {e}")

asyncio.run(test())

# test_imports.py

print("="*60)
print("Testing LangChain Imports for Version 1.1.3")
print("="*60)

# Test 1: AgentExecutor
print("\n[Test 1] AgentExecutor:")
try:
    from langchain.agents import AgentExecutor
    print("✓ SUCCESS: from langchain.agents import AgentExecutor")
except ImportError:
    try:
        from langchain_core.agents import AgentExecutor
        print("✓ SUCCESS: from langchain_core.agents import AgentExecutor")
    except ImportError as e:
        print(f"✗ FAILED: {e}")

# Test 2: create_structured_chat_agent
print("\n[Test 2] create_structured_chat_agent:")
try:
    from langchain.agents import create_structured_chat_agent
    print("✓ SUCCESS: from langchain.agents import create_structured_chat_agent")
except ImportError:
    try:
        from langchain.agents.structured_chat.base import create_structured_chat_agent
        print("✓ SUCCESS: from langchain.agents.structured_chat.base import create_structured_chat_agent")
    except ImportError as e:
        print(f"✗ FAILED: {e}")

# Test 3: What's available in langchain.agents?
print("\n[Test 3] Available in langchain.agents:")
try:
    import langchain.agents as la
    available = [x for x in dir(la) if not x.startswith('_') and 'agent' in x.lower()]
    print(f"Agent-related items: {available}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 4: BaseMemory
print("\n[Test 4] BaseMemory:")
try:
    from langchain_core.memory import BaseMemory
    print("✓ SUCCESS: from langchain_core.memory import BaseMemory")
except ImportError:
    try:
        from langchain.schema import BaseMemory
        print("✓ SUCCESS: from langchain.schema import BaseMemory")
    except ImportError:
        try:
            from langchain.memory import BaseMemory
            print("✓ SUCCESS: from langchain.memory import BaseMemory")
        except ImportError as e:
            print(f"✗ FAILED: {e}")

# Test 5: ConversationBufferWindowMemory
print("\n[Test 5] ConversationBufferWindowMemory:")
try:
    from langchain.memory import ConversationBufferWindowMemory
    print("✓ SUCCESS: from langchain.memory import ConversationBufferWindowMemory")
except ImportError:
    try:
        from langchain_classic.memory import ConversationBufferWindowMemory
        print("✓ SUCCESS: from langchain_classic.memory import ConversationBufferWindowMemory")
    except ImportError as e:
        print(f"✗ FAILED: {e}")

print("\n" + "="*60)
print("Testing Complete!")
print("="*60)
# Save this as test_imports.py

print("="*60)
print("Testing LangChain Imports")
print("="*60)

# Test AgentExecutor
print("\n1. Testing AgentExecutor:")
try:
    from langchain.agents import AgentExecutor
    print("   ✓ from langchain.agents import AgentExecutor")
except ImportError as e:
    print(f"   ✗ FAILED: {e}")

# Test create_structured_chat_agent
print("\n2. Testing create_structured_chat_agent:")
try:
    from langchain.agents import create_structured_chat_agent
    print("   ✓ from langchain.agents import create_structured_chat_agent")
except ImportError as e:
    print(f"   ✗ FAILED: {e}")



# Test ConversationBufferWindowMemory
print("\n4. Testing ConversationBufferWindowMemory:")
try:
    from langchain_classic.memory import ConversationBufferWindowMemory
    print("   ✓ from langchain.memory import ConversationBufferWindowMemory")
except ImportError as e:
    print(f"   ✗ FAILED: {e}")

# Check what's available
print("\n5. What's available in langchain.agents:")
try:
    import langchain.agents as la
    items = [x for x in dir(la) if not x.startswith('_')]
    print(f"   Found: {items[:10]}...")  # Show first 10
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "="*60)
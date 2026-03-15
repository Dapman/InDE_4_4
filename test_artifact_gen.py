"""Quick test for artifact generation."""
from database import db
from core.llm_interface import LLMInterface
from scaffolding.engine import ScaffoldingEngine
from config import DEMO_USER_ID

# Initialize
llm = LLMInterface()
engine = ScaffoldingEngine(db, llm)

# Create a pursuit with enough elements
result1 = engine.process_message('I want to create a safety app for seniors that monitors falls', user_id=DEMO_USER_ID)
pursuit_id = result1['pursuit_id']
print(f'Created pursuit: {pursuit_id}')

# Add more elements
engine.process_message('Seniors 65+ living alone who are at risk of falls', current_pursuit_id=pursuit_id, user_id=DEMO_USER_ID)
engine.process_message('Currently they have to press a button or call 911 which they often cannot do if injured', current_pursuit_id=pursuit_id, user_id=DEMO_USER_ID)
engine.process_message('The app uses phone sensors to auto-detect falls and alert family members', current_pursuit_id=pursuit_id, user_id=DEMO_USER_ID)
engine.process_message('It saves precious minutes in emergency response time and could save lives', current_pursuit_id=pursuit_id, user_id=DEMO_USER_ID)
engine.process_message('What makes it unique is the AI that learns normal movement patterns to reduce false alarms', current_pursuit_id=pursuit_id, user_id=DEMO_USER_ID)

# Check completeness
completeness = engine.element_tracker.get_completeness(pursuit_id)
print(f'====== After all messages ======')
print(f'Completeness: vision={completeness["vision"]*100:.0f}%')
print(f'Pending artifact BEFORE manual set: {engine._pending_artifact}')

# Manually set pending artifact to test
engine._pending_artifact = {
    'pursuit_id': pursuit_id,
    'artifact_type': 'vision'
}
print(f'Manually set pending_artifact: {engine._pending_artifact}')

# Test acceptance
result = engine.process_message('Yes please draft that vision statement', current_pursuit_id=pursuit_id, user_id=DEMO_USER_ID)
print(f'Intervention: {result["intervention_made"]}')
print(f'Artifacts generated: {len(result["artifacts_generated"])}')
if result['artifact_content']:
    print('=' * 50)
    print('ARTIFACT GENERATED SUCCESSFULLY!')
    print('=' * 50)
    print(result['artifact_content'][:500])
else:
    print('NO ARTIFACT GENERATED')
    print(f'Response: {result["response"][:200]}')

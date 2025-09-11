"""
Internal Task Tracker for OpenInterpreter
Manages multi-step tasks internally without user-facing output
"""
import json
import uuid
from typing import List, Dict, Optional
from datetime import datetime
import streamlit as st

class InternalTask:
    def __init__(self, task_id: str, description: str, priority: str = "medium"):
        self.id = task_id
        self.description = description
        self.status = "pending"  # pending, in_progress, completed, failed
        self.priority = priority  # low, medium, high
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.subtasks = []
        self.context = {}

    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'subtasks': self.subtasks,
            'context': self.context
        }

    @classmethod
    def from_dict(cls, data):
        task = cls(data['id'], data['description'], data['priority'])
        task.status = data['status']
        task.created_at = data['created_at']
        task.updated_at = data['updated_at']
        task.subtasks = data.get('subtasks', [])
        task.context = data.get('context', {})
        return task

class InternalTaskTracker:
    def __init__(self):
        self.session_key = "_internal_task_tracker"
        self._ensure_session_state()

    def _ensure_initialized(self):
        pass

    def _ensure_session_state(self):
        """Initialize session state for internal tracking"""
        if self.session_key not in st.session_state:
            st.session_state[self.session_key] = {
                'tasks': {},
                'active_task_id': None,
                'task_history': []
            }

    def _should_create_internal_task(self, user_message: str) -> bool:
        """Detect if a task requires multi-step internal tracking"""
        multi_step_indicators = [
            'create', 'build', 'develop', 'implement', 'design',
            'analyze', 'review', 'process', 'generate', 'setup',
            'configure', 'install', 'deploy', 'test', 'debug',
            'multiple', 'several', 'various', 'different',
            'step by step', 'phases', 'stages', 'milestones'
        ]
        
        message_lower = user_message.lower()
        return any(indicator in message_lower for indicator in multi_step_indicators)

    def create_task(self, description: str, priority: str = "medium", context: Dict = None) -> str:
        """Create a new internal task"""
        task_id = str(uuid.uuid4())[:8]
        task = InternalTask(task_id, description, priority)
        if context:
            task.context = context
        
        st.session_state[self.session_key]['tasks'][task_id] = task.to_dict()
        st.session_state[self.session_key]['active_task_id'] = task_id
        
        return task_id

    def add_subtask(self, task_id: str, subtask_description: str) -> bool:
        """Add a subtask to an existing task"""
        if task_id not in st.session_state[self.session_key]['tasks']:
            return False
        
        subtask = {
            'id': str(uuid.uuid4())[:8],
            'description': subtask_description,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        
        st.session_state[self.session_key]['tasks'][task_id]['subtasks'].append(subtask)
        st.session_state[self.session_key]['tasks'][task_id]['updated_at'] = datetime.now().isoformat()
        
        return True

    def update_task_status(self, task_id: str, status: str) -> bool:
        """Update task status"""
        if task_id not in st.session_state[self.session_key]['tasks']:
            return False
        
        st.session_state[self.session_key]['tasks'][task_id]['status'] = status
        st.session_state[self.session_key]['tasks'][task_id]['updated_at'] = datetime.now().isoformat()
        
        if status == 'completed':
            # Move to history
            task_data = st.session_state[self.session_key]['tasks'][task_id]
            st.session_state[self.session_key]['task_history'].append(task_data)
            
            # Clear active task if this was it
            if st.session_state[self.session_key]['active_task_id'] == task_id:
                st.session_state[self.session_key]['active_task_id'] = None
        
        return True

    def update_subtask_status(self, task_id: str, subtask_id: str, status: str) -> bool:
        """Update subtask status"""
        if task_id not in st.session_state[self.session_key]['tasks']:
            return False
        
        for subtask in st.session_state[self.session_key]['tasks'][task_id]['subtasks']:
            if subtask['id'] == subtask_id:
                subtask['status'] = status
                subtask['updated_at'] = datetime.now().isoformat()
                st.session_state[self.session_key]['tasks'][task_id]['updated_at'] = datetime.now().isoformat()
                return True
        
        return False

    def get_active_task(self) -> Optional[Dict]:
        """Get the currently active task"""
        active_id = st.session_state[self.session_key]['active_task_id']
        if active_id and active_id in st.session_state[self.session_key]['tasks']:
            return st.session_state[self.session_key]['tasks'][active_id]
        return None

    def get_task_progress(self, task_id: str) -> Dict:
        """Get task progress summary"""
        if task_id not in st.session_state[self.session_key]['tasks']:
            return {}
        
        task = st.session_state[self.session_key]['tasks'][task_id]
        subtasks = task.get('subtasks', [])
        
        if not subtasks:
            return {'progress': 0, 'completed': 0, 'total': 0}
        
        completed = sum(1 for st in subtasks if st['status'] == 'completed')
        total = len(subtasks)
        progress = (completed / total) * 100 if total > 0 else 0
        
        return {
            'progress': progress,
            'completed': completed,
            'total': total,
            'pending': sum(1 for st in subtasks if st['status'] == 'pending'),
            'in_progress': sum(1 for st in subtasks if st['status'] == 'in_progress')
        }

    def auto_manage_task(self, user_message: str, ai_response: str = None) -> Optional[str]:
        """Automatically manage task creation and updates based on context"""
        # Check if we should create a new task
        if self._should_create_internal_task(user_message):
            # Extract task description from user message
            task_desc = user_message[:100] + "..." if len(user_message) > 100 else user_message
            
            # Determine priority based on keywords
            priority = "high" if any(word in user_message.lower() for word in ['urgent', 'asap', 'critical', 'important']) else "medium"
            
            task_id = self.create_task(task_desc, priority, {'original_request': user_message})
            
            # Auto-generate subtasks based on common patterns
            self._auto_generate_subtasks(task_id, user_message)
            
            return task_id
        
        return None

    def _auto_generate_subtasks(self, task_id: str, user_message: str):
        """Auto-generate subtasks based on message content"""
        message_lower = user_message.lower()
        
        # Common task patterns and their subtasks
        if 'create' in message_lower or 'build' in message_lower:
            self.add_subtask(task_id, "Analyze requirements")
            self.add_subtask(task_id, "Design solution")
            self.add_subtask(task_id, "Implement core functionality")
            self.add_subtask(task_id, "Test and validate")
            self.add_subtask(task_id, "Finalize and deliver")
        
        elif 'analyze' in message_lower or 'review' in message_lower:
            self.add_subtask(task_id, "Gather and examine data")
            self.add_subtask(task_id, "Identify key patterns")
            self.add_subtask(task_id, "Generate insights")
            self.add_subtask(task_id, "Provide recommendations")
        
        elif 'setup' in message_lower or 'configure' in message_lower:
            self.add_subtask(task_id, "Check prerequisites")
            self.add_subtask(task_id, "Install dependencies")
            self.add_subtask(task_id, "Configure settings")
            self.add_subtask(task_id, "Verify setup")
        
        elif 'debug' in message_lower or 'fix' in message_lower:
            self.add_subtask(task_id, "Reproduce issue")
            self.add_subtask(task_id, "Identify root cause")
            self.add_subtask(task_id, "Implement solution")
            self.add_subtask(task_id, "Test fix")

    def mark_subtask_completed(self, subtask_description_partial: str) -> bool:
        """Mark a subtask as completed based on partial description match"""
        active_task = self.get_active_task()
        if not active_task:
            return False
        
        for subtask in active_task.get('subtasks', []):
            if subtask_description_partial.lower() in subtask['description'].lower():
                if subtask['status'] != 'completed':
                    self.update_subtask_status(active_task['id'], subtask['id'], 'completed')
                    return True
        
        return False

    def get_next_pending_subtask(self) -> Optional[Dict]:
        """Get the next pending subtask for the active task"""
        active_task = self.get_active_task()
        if not active_task:
            return None
        
        for subtask in active_task.get('subtasks', []):
            if subtask['status'] == 'pending':
                return subtask
        
        return None

    def cleanup_completed_tasks(self, max_history: int = 50):
        """Clean up old completed tasks to prevent memory bloat"""
        history = st.session_state[self.session_key]['task_history']
        if len(history) > max_history:
            st.session_state[self.session_key]['task_history'] = history[-max_history:]

# Global instance for use throughout the application
internal_tracker = InternalTaskTracker()

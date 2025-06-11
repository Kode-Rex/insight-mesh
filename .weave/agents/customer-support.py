import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from weave.agents import agent, BaseAgent
from typing import Dict, List, Any

@agent("customer-support", "person", "messages", "Resolve customer issues using conversation history and available tools")
class CustomerSupportAgent(BaseAgent):
    @property
    def domain(self) -> str:
        return "person"
    
    @property
    def context(self) -> str:
        return "messages"
    
    @property
    def goal(self) -> str:
        return """Help customers resolve issues by:
1. Understanding their problem from conversation history
2. Searching for solutions using available tools
3. Providing clear, actionable responses"""
    
    @property
    def tools(self) -> List[str]:
        return ["slack", "webcat", "notion"]
    
    @property
    def execution(self) -> Dict[str, Any]:
        return {
            "timeout": 300,
            "retry": 3,
            "cache": True,
            "memory_limit": "512Mi"
        }
    
    @property
    def observability(self) -> Dict[str, Any]:
        return {
            "trace": True,
            "metrics": True,
            "logs": "info"
        }
    
    @property
    def triggers(self) -> List[Dict[str, Any]]:
        return [
            {"type": "slack_mention", "pattern": "@support"},
            {"type": "webhook", "path": "/agents/customer-support"}
        ]
    
    @property
    def environment(self) -> Dict[str, Any]:
        return {
            "MODEL": "gpt-4o-mini",
            "MAX_TOKENS": 2000,
            "TEMPERATURE": 0.7
        }
    
    async def execute(self, query: str, **kwargs) -> str:
        """Execute the customer support agent logic"""
        # Classify the query type
        if any(word in query.lower() for word in ['billing', 'payment', 'invoice', 'charge']):
            query_type = 'billing'
        elif any(word in query.lower() for word in ['bug', 'error', 'broken', 'not working', 'crash', 'crashing']):
            query_type = 'technical'
        else:
            query_type = 'general'
        
        return f"Customer support agent processed {query_type} query: {query}" 
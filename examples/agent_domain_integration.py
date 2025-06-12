#!/usr/bin/env python3
"""
Agent Domain Integration Example

This demonstrates how AI agents can work with rich domain objects (User, 
Conversation, Document) to perform intelligent business operations across
multiple data sources.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any


class DocumentAnalysisAgent:
    """
    AI Agent that analyzes documents across all sources for insights.
    
    This agent can work with the Document domain object to provide
    intelligent document analysis, relationship discovery, and content insights.
    """
    
    def __init__(self, session_factories: Dict[str, Any]):
        self.session_factories = session_factories
    
    async def analyze_user_documents(self, user_id: str) -> Dict[str, Any]:
        """Analyze all documents associated with a user across all platforms."""
        from domain import Document, DocumentType
        
        # Find all documents for the user
        documents = await Document.find_documents_by_user(
            user_id=user_id,
            session_factories=self.session_factories
        )
        
        analysis = {
            'total_documents': len(documents),
            'by_type': {},
            'by_format': {},
            'recent_activity': [],
            'large_files': [],
            'text_documents': [],
            'sharing_patterns': {}
        }
        
        for doc in documents:
            # Categorize by type
            doc_type = doc.identity.document_type.value
            analysis['by_type'][doc_type] = analysis['by_type'].get(doc_type, 0) + 1
            
            # Categorize by format
            doc_format = doc.identity.format.value
            analysis['by_format'][doc_format] = analysis['by_format'].get(doc_format, 0) + 1
            
            # Track recent activity
            if doc.is_recent:
                analysis['recent_activity'].append({
                    'title': doc.title,
                    'type': doc_type,
                    'age_days': doc.age_days
                })
            
            # Track large files
            if doc.is_large:
                analysis['large_files'].append({
                    'title': doc.title,
                    'size_mb': doc.size_mb,
                    'type': doc_type
                })
            
            # Track text documents for content analysis
            if doc.is_text_based:
                analysis['text_documents'].append({
                    'title': doc.title,
                    'format': doc_format,
                    'related_conversations': len(doc.get_related_conversations())
                })
            
            # Analyze sharing patterns
            sharing_context = doc.get_sharing_context()
            source = sharing_context['source']
            if source not in analysis['sharing_patterns']:
                analysis['sharing_patterns'][source] = {
                    'count': 0,
                    'public_docs': 0,
                    'avg_related_users': 0
                }
            
            analysis['sharing_patterns'][source]['count'] += 1
            if sharing_context.get('is_public'):
                analysis['sharing_patterns'][source]['public_docs'] += 1
        
        return analysis
    
    async def find_duplicate_documents(self) -> List[Dict[str, Any]]:
        """Find potential duplicate documents across all sources."""
        from domain import Document
        
        # This would implement content-based deduplication
        # For now, return example structure
        duplicates = []
        
        # Example: Find documents with similar titles or content hashes
        # Implementation would use Document.calculate_content_hash() and similarity algorithms
        
        return duplicates
    
    async def recommend_document_cleanup(self, user_id: str) -> Dict[str, Any]:
        """Recommend document cleanup actions for a user."""
        analysis = await self.analyze_user_documents(user_id)
        
        recommendations = {
            'large_files_to_review': analysis['large_files'][:5],  # Top 5 largest
            'old_documents': [],  # Documents older than 1 year with no recent access
            'unshared_documents': [],  # Documents not shared in any conversation
            'format_conversions': []  # Suggest converting old formats
        }
        
        return recommendations


class ConversationIntelligenceAgent:
    """
    AI Agent that analyzes conversations for business insights.
    
    This agent works with Conversation domain objects to identify patterns,
    extract insights, and provide conversation analytics.
    """
    
    def __init__(self, session_factories: Dict[str, Any]):
        self.session_factories = session_factories
    
    async def analyze_topic_trends(self, topic: str, days: int = 30) -> Dict[str, Any]:
        """Analyze conversation trends for a specific topic."""
        from domain import Conversation
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        conversations = await Conversation.find_conversations_by_topic(
            topic=topic,
            date_range=(start_date, end_date),
            session_factories=self.session_factories
        )
        
        analysis = {
            'topic': topic,
            'period_days': days,
            'total_conversations': len(conversations),
            'total_messages': sum(conv.message_count for conv in conversations),
            'unique_participants': set(),
            'platform_distribution': {},
            'activity_timeline': {},
            'key_conversations': []
        }
        
        for conv in conversations:
            # Track unique participants
            analysis['unique_participants'].update(conv.identity.participants)
            
            # Platform distribution
            conv_type = conv.identity.conversation_type.value
            analysis['platform_distribution'][conv_type] = analysis['platform_distribution'].get(conv_type, 0) + 1
            
            # Activity timeline (by day)
            if conv.identity.start_date:
                day_key = conv.identity.start_date.strftime('%Y-%m-%d')
                if day_key not in analysis['activity_timeline']:
                    analysis['activity_timeline'][day_key] = {'conversations': 0, 'messages': 0}
                analysis['activity_timeline'][day_key]['conversations'] += 1
                analysis['activity_timeline'][day_key]['messages'] += conv.message_count
            
            # Key conversations (most active)
            if conv.message_count > 5:  # Threshold for "key" conversation
                analysis['key_conversations'].append({
                    'title': conv.identity.title,
                    'messages': conv.message_count,
                    'participants': conv.participant_count,
                    'duration_hours': conv.duration.total_seconds() / 3600 if conv.duration else None,
                    'is_active': conv.is_active
                })
        
        # Convert set to count
        analysis['unique_participants'] = len(analysis['unique_participants'])
        
        # Sort key conversations by message count
        analysis['key_conversations'].sort(key=lambda x: x['messages'], reverse=True)
        analysis['key_conversations'] = analysis['key_conversations'][:10]  # Top 10
        
        return analysis
    
    async def identify_knowledge_gaps(self, user_id: str) -> Dict[str, Any]:
        """Identify topics where user asked questions but didn't get satisfactory answers."""
        from domain import User, Conversation
        
        # Get user's conversations
        user = await User.from_insightmesh_id(user_id, self.session_factories)
        if not user:
            return {'error': 'User not found'}
        
        conversations = await user.get_conversations(self.session_factories)
        
        knowledge_gaps = {
            'unanswered_questions': [],
            'incomplete_conversations': [],
            'topics_needing_followup': []
        }
        
        for conv_data in conversations:
            # Convert to domain conversation
            domain_conv = await Conversation.from_insightmesh_conversation(conv_data, self.session_factories)
            
            # Analyze user messages for questions
            user_messages = domain_conv.get_messages_by_participant(user_id)
            
            # Simple heuristic: messages ending with '?' are questions
            questions = [msg for msg in user_messages if msg['content'].strip().endswith('?')]
            
            if questions:
                # Check if conversation continued after questions (indicating answers)
                last_question_time = max(msg['timestamp'] for msg in questions)
                all_messages = domain_conv.get_all_messages()
                
                # Messages after last question
                followup_messages = [
                    msg for msg in all_messages 
                    if msg['timestamp'] > last_question_time and msg['author_id'] != user_id
                ]
                
                if not followup_messages:
                    knowledge_gaps['unanswered_questions'].append({
                        'conversation_title': domain_conv.identity.title,
                        'questions': [msg['content'] for msg in questions],
                        'last_question_date': last_question_time.isoformat()
                    })
        
        return knowledge_gaps
    
    async def suggest_conversation_connections(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Suggest related conversations based on participants and topics."""
        from domain import Conversation
        
        # This would implement conversation similarity analysis
        # For now, return example structure
        suggestions = []
        
        return suggestions


class UserEngagementAgent:
    """
    AI Agent that analyzes user engagement across all platforms.
    
    This agent works with User domain objects to provide insights about
    user activity, preferences, and engagement patterns.
    """
    
    def __init__(self, session_factories: Dict[str, Any]):
        self.session_factories = session_factories
    
    async def analyze_user_engagement(self, email: str) -> Dict[str, Any]:
        """Analyze user engagement across all platforms."""
        from domain import User, Conversation, Document
        
        user = await User.from_email(email, self.session_factories)
        if not user:
            return {'error': 'User not found'}
        
        engagement = {
            'user_identity': {
                'name': user.name,
                'email': user.email,
                'sources': user.get_loaded_sources(),
                'is_active': user.is_active
            },
            'platform_presence': {
                'slack': user.has_slack_presence(),
                'insightmesh': user.has_insightmesh_account()
            },
            'activity_summary': {},
            'preferences': {},
            'recommendations': []
        }
        
        # Analyze conversations
        if user.has_insightmesh_account():
            conversations = await user.get_conversations(self.session_factories)
            engagement['activity_summary']['conversations'] = len(conversations)
            
            # Analyze conversation patterns
            if conversations:
                recent_conversations = [
                    conv for conv in conversations 
                    if conv.updated_at and (datetime.utcnow() - conv.updated_at).days <= 7
                ]
                engagement['activity_summary']['recent_conversations'] = len(recent_conversations)
        
        # Analyze documents
        documents = await Document.find_documents_by_user(
            user_id=user.identity.primary_id,
            session_factories=self.session_factories
        )
        engagement['activity_summary']['documents'] = len(documents)
        
        # Generate recommendations
        if engagement['activity_summary'].get('conversations', 0) == 0:
            engagement['recommendations'].append("Consider starting a conversation to get help with your questions")
        
        if not user.has_slack_presence():
            engagement['recommendations'].append("Connect your Slack account for better collaboration")
        
        return engagement
    
    async def identify_power_users(self) -> List[Dict[str, Any]]:
        """Identify users with high engagement across platforms."""
        # This would analyze all users and rank by engagement metrics
        power_users = []
        
        return power_users


def show_agent_capabilities():
    """Show how agents can work with domain objects."""
    print("AI Agent Integration with Domain Objects")
    print("=" * 50)
    
    print("\n🤖 DOCUMENT ANALYSIS AGENT:")
    print("  • Analyze user documents across all platforms")
    print("  • Find duplicate documents using content hashing")
    print("  • Recommend document cleanup actions")
    print("  • Track document sharing patterns")
    print("  • Identify large/old files for optimization")
    
    print("\n💬 CONVERSATION INTELLIGENCE AGENT:")
    print("  • Analyze topic trends across platforms")
    print("  • Identify knowledge gaps and unanswered questions")
    print("  • Suggest related conversations")
    print("  • Track conversation activity patterns")
    print("  • Generate conversation insights")
    
    print("\n👥 USER ENGAGEMENT AGENT:")
    print("  • Analyze user engagement across platforms")
    print("  • Identify power users and engagement patterns")
    print("  • Generate personalized recommendations")
    print("  • Track cross-platform activity")
    print("  • Suggest platform connections")
    
    print("\n🎯 BUSINESS VALUE:")
    print("  • Rich domain objects provide context for AI")
    print("  • Cross-platform insights impossible with raw data")
    print("  • Business-focused analysis and recommendations")
    print("  • Unified view enables intelligent automation")


async def demonstrate_agent_workflows():
    """Demonstrate example agent workflows."""
    print("\n" + "=" * 50)
    print("EXAMPLE AGENT WORKFLOWS")
    print("=" * 50)
    
    print("\n📊 Document Analysis Workflow:")
    print("1. agent = DocumentAnalysisAgent(session_factories)")
    print("2. analysis = await agent.analyze_user_documents('user_123')")
    print("3. recommendations = await agent.recommend_document_cleanup('user_123')")
    print("4. # Agent provides insights like:")
    print("   # - 'You have 15 large files taking up 150MB'")
    print("   # - 'Found 3 potential duplicate documents'")
    print("   # - 'Consider archiving 8 old documents'")
    
    print("\n💡 Conversation Intelligence Workflow:")
    print("1. agent = ConversationIntelligenceAgent(session_factories)")
    print("2. trends = await agent.analyze_topic_trends('machine learning', days=30)")
    print("3. gaps = await agent.identify_knowledge_gaps('user_123')")
    print("4. # Agent provides insights like:")
    print("   # - 'ML discussions increased 40% this month'")
    print("   # - 'You asked 5 questions about Python but got no responses'")
    print("   # - 'Similar topics discussed in 3 other conversations'")
    
    print("\n🎯 User Engagement Workflow:")
    print("1. agent = UserEngagementAgent(session_factories)")
    print("2. engagement = await agent.analyze_user_engagement('john@company.com')")
    print("3. power_users = await agent.identify_power_users()")
    print("4. # Agent provides insights like:")
    print("   # - 'User active on Slack but not using AI features'")
    print("   # - 'Recommend connecting platforms for better experience'")
    print("   # - 'Top 10 most engaged users across all platforms'")


async def main():
    """Run the agent integration demonstration."""
    show_agent_capabilities()
    await demonstrate_agent_workflows()
    
    print("\n" + "=" * 50)
    print("🚀 AGENTS + DOMAIN OBJECTS = INTELLIGENCE!")
    print("=" * 50)
    print("✅ Rich business context for AI agents")
    print("✅ Cross-platform insights and analysis")
    print("✅ Intelligent automation and recommendations")
    print("✅ Business-focused rather than data-focused")
    print("✅ Unified view enables sophisticated workflows")


if __name__ == "__main__":
    asyncio.run(main()) 
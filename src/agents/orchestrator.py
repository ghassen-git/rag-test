
from typing import Dict, Any, TypedDict, Annotated

from langchain_openai import ChatOpenAI
import logging
import operator

from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from src.agents.analyst_agent import analyst_agent
from src.agents.search_agent import search_agent
from src.config import settings
logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    
    query: str
    intent: str
    search_results: list
    book_data: dict
    review_data: dict
    context: str
    final_answer: str
    action_result: dict
    messages: Annotated[list, operator.add]

class OrchestratorAgent:

    def __init__(self):
        
        self.name = "OrchestratorAgent"
        self.llm = ChatOpenAI(
            model=settings.openai_llm_model,
            api_key=settings.openai_api_key,
            temperature=0.7
        )
        
        # Build the agent graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze_intent", self._analyze_intent)
        workflow.add_node("search_vectors", self._search_vectors)
        workflow.add_node("query_databases", self._query_databases)
        workflow.add_node("execute_action", self._execute_action)
        workflow.add_node("synthesize_answer", self._synthesize_answer)
        
        # Define edges
        workflow.set_entry_point("analyze_intent")
        
        # Conditional routing based on intent
        workflow.add_conditional_edges(
            "analyze_intent",
            self._route_by_intent,
            {
                "search": "search_vectors",
                "data": "query_databases",
                "hybrid": "search_vectors",
                "action": "execute_action"
            }
        )
        
        workflow.add_edge("search_vectors", "query_databases")
        workflow.add_edge("query_databases", "synthesize_answer")
        workflow.add_edge("execute_action", "synthesize_answer")
        workflow.add_edge("synthesize_answer", END)
        
        return workflow.compile()
    
    async def _analyze_intent(self, state: AgentState) -> AgentState:
        
        query = state["query"]
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""Analyze the user's query and classify the intent into ONE of these categories:
- "action" - if the user wants to UPDATE, CHANGE, ADD, DELETE, or MODIFY data (e.g., "change rating", "update book", "add review")
- "search" - if the user wants to FIND or SEARCH for information (e.g., "find books about", "search for")
- "data" - if the user wants to GET or RETRIEVE structured data (e.g., "what is the rating", "show me books")
- "hybrid" - if the query combines multiple intents

Respond with ONLY ONE WORD: action, search, data, or hybrid."""),
            HumanMessage(content=f"Query: {query}")
        ])
        
        response = await self.llm.ainvoke(prompt.format_messages())
        intent = response.content.strip().lower()
        
        # Extract just the intent word if LLM added extra text
        if "action" in intent:
            intent = "action"
        elif "search" in intent:
            intent = "search"
        elif "data" in intent:
            intent = "data"
        else:
            intent = "hybrid"
        
        logger.info(f"Classified intent: {intent}")
        
        state["intent"] = intent
        state["messages"] = [f"Intent classified as: {intent}"]
        
        return state
    
    def _route_by_intent(self, state: AgentState) -> str:
        
        intent = state.get("intent", "hybrid")
        
        if intent == "search":
            return "search"
        elif intent == "data":
            return "data"
        elif intent == "action":
            return "action"
        else:
            return "hybrid"
    
    async def _search_vectors(self, state: AgentState) -> AgentState:
        
        query = state["query"]
        
        results = await search_agent.search(query, top_k=10)
        
        state["search_results"] = results
        state["messages"].append(f"Found {len(results)} relevant passages")
        
        logger.info(f"Search completed: {len(results)} results")
        
        return state
    
    async def _query_databases(self, state: AgentState) -> AgentState:
        
        query = state["query"]
        search_results = state.get("search_results", [])
        intent = state.get("intent", "")
        
        # Extract book IDs from search results
        book_ids = list(
            set([r["book_id"] for r in search_results if r.get("book_id")])
        )
        
        if not book_ids and intent == "data":
            # Get all books from analyst agent
            all_books = analyst_agent.get_all_books()
            if all_books:

                book_ids = [book["id"] for book in all_books[:5]]
                logger.info(
                    f"No search results, retrieved {len(book_ids)} books"
                )
        
        book_data = {}
        review_data = {}
        
        # Query book metadata and reviews
        for book_id in book_ids[:5]:  # Limit to top 5 books
            book = analyst_agent.get_book_by_id(book_id)
            if book:
                book_data[book_id] = book
                
                # Get review statistics
                review_stats = analyst_agent.get_review_statistics(book_id)
                reviews = analyst_agent.get_reviews_for_book(book_id)
                review_data[book_id] = {
                    "statistics": review_stats,
                    "reviews": reviews[:3]  # Top 3 reviews
                }
        
        state["book_data"] = book_data
        state["review_data"] = review_data
        state["messages"].append(f"Retrieved data for {len(book_data)} books")
        
        logger.info(f"Database query completed: {len(book_data)} books")
        
        return state
    
    async def _execute_action(self, state: AgentState) -> AgentState:
        
        query = state["query"]
        
        # Use LLM to extract action parameters
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""Extract action parameters from the user's query and return ONLY valid JSON.

For UPDATE RATING actions, return:
{
  "action_type": "update_rating",
  "book_title": "exact book title from query",
  "book_id": "unknown",
  "new_rating": 4.5
}

For ADD REVIEW actions, return:
{
  "action_type": "add_review",
  "book_title": "exact book title from query",
  "book_id": "unknown",
  "review_text": "review content",
  "review_rating": 5,
  "user_id": "user_001",
  "username": "System User"
}

Return ONLY the JSON object, no other text."""),
            HumanMessage(content=f"Query: {query}")
        ])
        
        response = await self.llm.ainvoke(prompt.format_messages())
        
        try:
            import json
            import re
            
            # Extract JSON from response
            content = response.content.strip()
            # Remove markdown code blocks if present
            content = re.sub(r'```json\s*|\s*```', '', content)
            params = json.loads(content)
            
            action_type = params.get("action_type")
            book_id = params.get("book_id")
            book_title = params.get("book_title")

            if book_id == "unknown" and book_title != "unknown":
                # Ensure analyst agent is connected
                if not analyst_agent.pg_conn:
                    analyst_agent.connect()
                
                all_books = analyst_agent.get_all_books()
                for book in all_books:
                    if book_title.lower() in book.get("title", "").lower():
                        book_id = str(book["id"])
                        break
            
            # If still unknown, use the first book
            if book_id == "unknown":
                if not analyst_agent.pg_conn:
                    analyst_agent.connect()
                all_books = analyst_agent.get_all_books()
                if all_books:
                    book_id = str(all_books[0]["id"])
            
            result = {}
            
            if action_type == "update_rating":
                new_rating = float(params.get("new_rating", 0))
                if new_rating > 0 and book_id != "unknown":
                    # Ensure analyst agent is connected
                    if not analyst_agent.pg_conn:
                        analyst_agent.connect()
                    
                    success = analyst_agent.update_book_rating(book_id, new_rating)
                    result = {
                        "action": "update_rating",
                        "success": success,
                        "book_id": book_id,
                        "new_rating": new_rating,
                        "message": f"Rating updated to {new_rating}" if success else "Failed to update rating"
                    }
                else:
                    result = {
                        "action": "update_rating",
                        "success": False,
                        "message": "Invalid rating or book ID"
                    }
            
            elif action_type == "add_review":
                review_text = params.get("review_text")
                review_rating = int(params.get("review_rating", 5))
                user_id = params.get("user_id", "user_001")
                username = params.get("username", "System User")
                
                if review_text and book_id != "unknown":
                    # Ensure analyst agent is connected
                    if not analyst_agent.mongo_client:
                        analyst_agent.connect()
                    
                    from datetime import datetime
                    review_data = {
                        "book_id": book_id,
                        "user_id": user_id,
                        "username": username,
                        "rating": review_rating,
                        "review_text": review_text,
                        "helpful_count": 0,
                        "created_at": datetime.now()
                    }
                    success = analyst_agent.add_review(review_data)
                    result = {
                        "action": "add_review",
                        "success": success,
                        "book_id": book_id,
                        "review_text": review_text,
                        "rating": review_rating,
                        "message": "Review added successfully" if success else "Failed to add review"
                    }
                else:
                    result = {
                        "action": "add_review",
                        "success": False,
                        "message": "Invalid review text or book ID"
                    }
            
            state["action_result"] = result
            state["messages"].append(f"Action executed: {result.get('message', 'Unknown')}")
            
            logger.info(f"Action executed: {result}")
            
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            state["action_result"] = {
                "success": False,
                "message": f"Error: {str(e)}"
            }
            state["messages"].append(f"Action failed: {str(e)}")
        
        return state
    
    async def _synthesize_answer(self, state: AgentState) -> AgentState:
        
        query = state["query"]
        intent = state.get("intent", "")
        search_results = state.get("search_results", [])
        book_data = state.get("book_data", {})
        review_data = state.get("review_data", {})
        action_result = state.get("action_result", {})
        
        if intent == "action" and action_result:
            if action_result.get("success"):
                action_type = action_result.get("action")
                if action_type == "update_rating":
                    final_answer = f"✅ Successfully updated the book rating to {action_result.get('new_rating')}/5 for book ID {action_result.get('book_id')}."
                elif action_type == "add_review":
                    final_answer = f"✅ Successfully added your review with a {action_result.get('rating')}/5 rating for book ID {action_result.get('book_id')}."
                else:
                    final_answer = f"✅ {action_result.get('message', 'Action completed successfully')}"
            else:
                final_answer = f"❌ {action_result.get('message', 'Action failed')}"
            
            state["final_answer"] = final_answer
            state["messages"].append("Action result synthesized")
            return state
        
        # Build context for read queries
        context = self._build_context(search_results, book_data, review_data)
        state["context"] = context
        
        # Generate answer
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="Generate a comprehensive answer based on the context provided."),
            HumanMessage(content=f"Query: {query}\n\nContext: {context}")
        ])
        
        response = await self.llm.ainvoke(prompt.format_messages())
        final_answer = response.content
        
        state["final_answer"] = final_answer
        state["messages"].append("Answer synthesized")
        
        logger.info("Answer synthesis completed")
        
        return state
    
    def _build_context(
        self,
        search_results: list,
        book_data: dict,
        review_data: dict
    ) -> str:
        
        context = ""
        
        if search_results:
            context += "\n"
            for i, result in enumerate(search_results[:10], 1):  # Increased from 5 to 10
                context += f"\n"
                context += f"**From:** {result['title']} by {result['author']}\n"
                context += f"**Source:** {result['source']}"
                if result.get('chapter', 0) > 0:
                    context += f" | Chapter {result['chapter']}"
                if result.get('page_number', 0) > 0:
                    context += f" | Page {result['page_number']}"
                context += f"\n\n**Content:**\n{result['content']}\n\n"
                context += "---\n\n"
            
            logger.info(f"Added {len(search_results[:10])} passages to context")
        else:
            logger.warning("No search results to add to context!")
        
        # Add book metadata
        if book_data:
            context += "## Book Metadata:\n\n"
            for book_id, book in book_data.items():
                context += analyst_agent.format_book_info(book)
                context += "\n"
        
        # Add review data
        if review_data:
            context += "## Reviews and Ratings:\n\n"
            for book_id, data in review_data.items():
                stats = data.get("statistics", {})
                reviews = data.get("reviews", [])
                
                book = book_data.get(book_id, {})
                title = book.get("title", f"Book {book_id}")
                
                context += f"### {title}\n"
                context += f"- Total Reviews: {stats.get('total_reviews', 0)}\n"
                context += f"- Average Rating: {stats.get('average_rating', 0)}/5\n\n"
                
                if reviews:
                    context += "**Sample Reviews:**\n\n"
                    for review in reviews[:2]:
                        context += f"- Rating: {review.get('rating', 0)}/5\n"
                        context += f"  {review.get('review_text', '')}\n\n"
                
                context += "---\n\n"
        
        return context
    
    async def process_query(self, query: str) -> Dict[str, Any]:
        
        try:
            # Initialize state
            initial_state = {
                "query": query,
                "intent": "",
                "search_results": [],
                "book_data": {},
                "review_data": {},
                "context": "",
                "final_answer": "",
                "action_result": {},
                "messages": []
            }
            
            # Run the graph
            final_state = await self.graph.ainvoke(initial_state)
            
            return {
                "answer": final_state["final_answer"],
                "intent": final_state["intent"],
                "search_results": final_state["search_results"],
                "book_data": final_state["book_data"],
                "action_result": final_state.get("action_result", {}),
                "context": final_state["context"],
                "messages": final_state["messages"]
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "answer": f"I encountered an error processing your query: {str(e)}",
                "intent": "error",
                "search_results": [],
                "book_data": {},
                "context": "",
                "messages": [f"Error: {str(e)}"]
            }
    
    def process_query_sync(self, query: str) -> Dict[str, Any]:
        """Synchronous wrapper for process_query method"""
        import asyncio
        
        # Create a new event loop for this synchronous call
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(self.process_query(query))
            return result
        finally:
            loop.close()

# Global orchestrator instance
orchestrator = OrchestratorAgent()

# Alias for backward compatibility
Orchestrator = OrchestratorAgent

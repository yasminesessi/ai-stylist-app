from typing import List, Dict
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.agents.state import OutfitAgentState
import json


class OutfitRecommenderAgent:
    """LangGraph-based agent for outfit recommendations"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.7,
            openai_api_key=settings.OPENAI_API_KEY
        )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        # Initialize StateGraph with state schema
        workflow = StateGraph(state_schema=OutfitAgentState)
        
        # Add nodes
        workflow.add_node("analyze_request", self._analyze_request_node)
        workflow.add_node("filter_wardrobe", self._filter_wardrobe_node)
        workflow.add_node("generate_outfits", self._generate_outfits_node)
        workflow.add_node("evaluate_outfits", self._evaluate_outfits_node)
        
        # Define edges using START and END constants
        workflow.add_edge(START, "analyze_request")
        workflow.add_edge("analyze_request", "filter_wardrobe")
        workflow.add_edge("filter_wardrobe", "generate_outfits")
        workflow.add_edge("generate_outfits", "evaluate_outfits")
        workflow.add_edge("evaluate_outfits", END)
        
        return workflow.compile()
    
    async def _analyze_request_node(self, state: OutfitAgentState) -> Dict:
        """Analyze the outfit request and extract key requirements
        
        Returns partial state update with only the 'reasoning' key
        """
        request = state["request"]
        user_profile = state["user_profile"]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a fashion expert analyzing outfit requests.
            Given the user's personality, preferences, and the occasion, identify:
            1. Key style elements needed
            2. Color palette suggestions
            3. Formality level
            4. Weather considerations
            
            Provide analysis in JSON format with keys: style_direction, colors, formality, weather_notes"""),
            ("user", """
            User Personality: {personality}
            Style Preferences: {preferences}
            Request: Occasion: {occasion}, Season: {season}, Weather: {weather}, Mood: {mood}
            """)
        ])
        
        response = await self.llm.ainvoke(
            prompt.format_messages(
                personality=json.dumps(user_profile.get("personality", {})),
                preferences=json.dumps(user_profile.get("style_preferences", {})),
                occasion=request.get("occasion", "casual"),
                season=request.get("season", "all_season"),
                weather=request.get("weather", "normal"),
                mood=request.get("mood", "neutral")
            )
        )
        
        # Return only the keys we're updating
        return {"reasoning": response.content}
    
    async def _filter_wardrobe_node(self, state: OutfitAgentState) -> Dict:
        """Filter wardrobe items based on request criteria
        
        Returns partial state update with only the 'filtered_items' key
        """
        wardrobe = state["wardrobe_items"]
        request = state["request"]
        
        # Group items by category
        filtered = {
            "tops": [],
            "bottoms": [],
            "dresses": [],
            "outerwear": [],
            "shoes": [],
            "accessories": []
        }
        
        occasion = request.get("occasion", "casual")
        season = request.get("season")
        
        for item in wardrobe:
            # Filter by occasion
            if occasion in item.get("occasions", []):
                # Filter by season if specified
                if season is None or season in item.get("seasons", []) or "all_season" in item.get("seasons", []):
                    category = item.get("category", "")
                    if category in filtered:
                        filtered[category].append(item)
        
        return {"filtered_items": filtered}
    
    async def _generate_outfits_node(self, state: OutfitAgentState) -> Dict:
        """Generate outfit combinations using AI
        
        Returns partial state update with only the 'outfit_suggestions' key
        """
        filtered_items = state["filtered_items"]
        request = state["request"]
        user_profile = state["user_profile"]
        
        # Create a prompt for the LLM to suggest outfit combinations
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert fashion stylist. Create cohesive outfit combinations.
            Consider color harmony, style consistency, and appropriateness for the occasion.
            Return a JSON array of outfits with item IDs and reasoning."""),
            ("user", """
            Available Items:
            Tops: {tops}
            Bottoms: {bottoms}
            Dresses: {dresses}
            Outerwear: {outerwear}
            Shoes: {shoes}
            Accessories: {accessories}
            
            User Personality: {personality}
            Preferred Colors: {preferred_colors}
            Occasion: {occasion}
            
            Create {num_suggestions} outfit suggestions. For each outfit, specify:
            - item_ids: list of item IDs to combine
            - reasoning: why this outfit works
            - style_description: overall style and vibe
            
            Return as JSON array: [{{"item_ids": [...], "reasoning": "...", "style_description": "..."}}, ...]
            """)
        ])
        
        response = await self.llm.ainvoke(
            prompt.format_messages(
                tops=json.dumps([{"id": str(i["_id"]), "name": i["name"], "color": i["color"]} 
                                 for i in filtered_items.get("tops", [])]),
                bottoms=json.dumps([{"id": str(i["_id"]), "name": i["name"], "color": i["color"]} 
                                    for i in filtered_items.get("bottoms", [])]),
                dresses=json.dumps([{"id": str(i["_id"]), "name": i["name"], "color": i["color"]} 
                                    for i in filtered_items.get("dresses", [])]),
                outerwear=json.dumps([{"id": str(i["_id"]), "name": i["name"], "color": i["color"]} 
                                      for i in filtered_items.get("outerwear", [])]),
                shoes=json.dumps([{"id": str(i["_id"]), "name": i["name"], "color": i["color"]} 
                                  for i in filtered_items.get("shoes", [])]),
                accessories=json.dumps([{"id": str(i["_id"]), "name": i["name"], "color": i["color"]} 
                                        for i in filtered_items.get("accessories", [])]),
                personality=json.dumps(user_profile.get("personality", {})),
                preferred_colors=json.dumps(user_profile.get("style_preferences", {}).get("preferred_colors", [])),
                occasion=request.get("occasion", "casual"),
                num_suggestions=request.get("num_suggestions", 3)
            )
        )
        
        # Parse the AI response
        try:
            content = response.content
            # Extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            outfit_suggestions = json.loads(content)
        except json.JSONDecodeError:
            outfit_suggestions = []
        
        return {"outfit_suggestions": outfit_suggestions}
    
    async def _evaluate_outfits_node(self, state: OutfitAgentState) -> Dict:
        """Evaluate and score outfit suggestions
        
        Returns partial state update with updated 'outfit_suggestions'
        """
        outfit_suggestions = state["outfit_suggestions"]
        
        # Add confidence scores to each outfit
        for outfit in outfit_suggestions:
            # Base confidence score
            outfit["confidence_score"] = 0.85
        
        return {"outfit_suggestions": outfit_suggestions}
    
    async def recommend_outfits(self, user_profile: Dict, wardrobe_items: List[Dict], 
                               request: Dict) -> Dict:
        """Main method to get outfit recommendations"""
        initial_state = {
            "user_profile": user_profile,
            "wardrobe_items": wardrobe_items,
            "request": request,
            "filtered_items": {},
            "outfit_suggestions": [],
            "reasoning": ""
        }
        
        # Run the graph
        result = await self.graph.ainvoke(initial_state)
        
        return {
            "suggestions": result["outfit_suggestions"],
            "reasoning": result["reasoning"],
            "filtered_items": result["filtered_items"]
        }


# Singleton instance
outfit_agent = OutfitRecommenderAgent()
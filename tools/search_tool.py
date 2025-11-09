"""Tavily search tool with robust error handling."""
import os
from typing import Optional

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    print("Warning: tavily-python not installed. Run: pip install tavily-python")


class SearchTool:
    """Web search using Tavily API."""
    
    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "TAVILY_API_KEY not found in environment. "
                "Get one free at: https://tavily.com"
            )
        
        if not TAVILY_AVAILABLE:
            raise ImportError(
                "tavily-python not installed. "
                "Install with: pip install tavily-python"
            )
        
        self.client = TavilyClient(api_key=self.api_key)
    
    def run(self, query: str, max_results: int = 5) -> str:
        """Execute search and return formatted results."""
        try:
            print(f"🔍 Searching: {query[:50]}...")
            
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth="basic",  # or "advanced" for more thorough
                include_answer=True,
                include_raw_content=False
            )
            
            # Format results
            results = []
            
            # Add AI-generated answer if available
            if response.get("answer"):
                results.append(f"Summary: {response['answer']}")
            
            # Add search results
            if response.get("results"):
                results.append("\nSources:")
                for i, result in enumerate(response["results"][:max_results], 1):
                    title = result.get("title", "No title")
                    content = result.get("content", "")[:200]
                    url = result.get("url", "")
                    
                    results.append(
                        f"\n{i}. {title}\n"
                        f"   {content}...\n"
                        f"   {url}"
                    )
            
            if not results:
                return f"No results found for: {query}"
            
            return "\n".join(results)
            
        except Exception as e:
            error_msg = f"Search failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            # Provide helpful error messages
            if "rate limit" in str(e).lower():
                return "Search failed: Rate limit exceeded. Please try again in a moment."
            elif "authentication" in str(e).lower() or "api key" in str(e).lower():
                return "Search failed: Invalid API key. Check your TAVILY_API_KEY in .env"
            elif "network" in str(e).lower() or "connection" in str(e).lower():
                return "Search failed: Network error. Check your internet connection."
            else:
                return f"Search failed: {str(e)}"


# Test function
def test_search():
    """Test the search tool."""
    try:
        tool = SearchTool()
        result = tool.run("What is Python programming language?", max_results=3)
        print("✅ Search test successful!")
        print(result[:200])
        return True
    except Exception as e:
        print(f"❌ Search test failed: {e}")
        return False


if __name__ == "__main__":
    test_search()
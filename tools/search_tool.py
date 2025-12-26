# # # """Tavily search tool with robust error handling."""
# # import os
# # from typing import Optional
# # from  dotenv import load_dotenv
# # load_dotenv()
# # try:
# #     from tavily import TavilyClient
# #     TAVILY_AVAILABLE = True
# # except ImportError:
# #     TAVILY_AVAILABLE = False
# #     print("Warning: tavily-python not installed. Run: pip install tavily-python")


# # class SearchTool:
# #     """Web search using Tavily API."""
    
# #     def __init__(self):
# #         self.api_key = os.getenv("TAVILY_API_KEY")
        
# #         if not self.api_key:
# #             raise ValueError(
# #                 "TAVILY_API_KEY not found in environment. "
# #                 "Get one free at: https://tavily.com"
# #             )
        
# #         if not TAVILY_AVAILABLE:
# #             raise ImportError(
# #                 "tavily-python not installed. "
# #                 "Install with: pip install tavily-python"
# #             )
        
# #         self.client = TavilyClient(api_key=self.api_key)
    
# # #     # def run(self, query: str, max_results: int = 5) -> str:
# # #     #     """Execute search and return formatted results."""
# # #     #     try:
# # #     #         print(f"🔍 Searching: {query[:50]}...")
            
# # #     #         response = self.client.search(
# # #     #             query=query,
# # #     #             max_results=max_results,
# # #     #             search_depth="basic",  # or "advanced" for more thorough
# # #     #             include_answer=True,
# # #     #             include_raw_content=False
# # #     #         )
            
# # #     #         # Format results
# # #     #         results = []
            
# # #     #         # Add AI-generated answer if available
# # #     #         if response.get("answer"):
# # #     #             results.append(f"Summary: {response['answer']}")
            
# # #     #         # Add search results
# # #     #         if response.get("results"):
# # #     #             results.append("\nSources:")
# # #     #             for i, result in enumerate(response["results"][:max_results], 1):
# # #     #                 title = result.get("title", "No title")
# # #     #                 content = result.get("content", "")[:200]
# # #     #                 url = result.get("url", "")
                    
# # #     #                 results.append(
# # #     #                     f"\n{i}. {title}\n"
# # #     #                     f"   {content}...\n"
# # #     #                     f"   {url}"
# # #     #                 )
            
# # #     #         if not results:
# # #     #             return f"No results found for: {query}"
            
# # #     #         return "\n".join(results)
            
# # #     #     except Exception as e:
# # #     #         error_msg = f"Search failed: {str(e)}"
# # #     #         print(f" {error_msg}")
            
# # #     #         # Provide helpful error messages
# # #     #         if "rate limit" in str(e).lower():
# # #     #             return "Search failed: Rate limit exceeded. Please try again in a moment."
# # #     #         elif "authentication" in str(e).lower() or "api key" in str(e).lower():
# # #     #             return "Search failed: Invalid API key. Check your TAVILY_API_KEY in .env"
# # #     #         elif "network" in str(e).lower() or "connection" in str(e).lower():
# # #     #             return "Search failed: Network error. Check your internet connection."
# # #     #         else:
# # #     #             return f"Search failed: {str(e)}"
# # #     def run(self, query: str, max_results: int = 5) -> dict:
# # #     """
# # #     Execute search and return:
# # #     - formatted_text (string for display)
# # #     - answer (AI-generated summary)
# # #     - sources (structured list of resources)
# # #     """
# # #         try:
# # #             print(f"🔍 Searching: {query[:50]}...")

# # #             response = self.client.search(
# # #                 query=query,
# # #                 max_results=max_results,
# # #                 search_depth="basic",  # or "advanced"
# # #                 include_answer=True,
# # #                 include_raw_content=False
# # #             )

# # #             answer = response.get("answer", "")
# # #             sources = []

# # #         # Collect sources in structured form
# # #         if response.get("results"):
# # #             for result in response["results"][:max_results]:
# # #                 sources.append({
# # #                     "title": result.get("title", "No title"),
# # #                     "url": result.get("url", ""),
# # #                     "snippet": result.get("content", "")[:200]
# # #                 })

# # #         # Build formatted text (same as before)
# # #         formatted_parts = []

# # #         if answer:
# # #             formatted_parts.append(f"Summary: {answer}")

# # #         if sources:
# # #             formatted_parts.append("\nSources:")
# # #             for i, src in enumerate(sources, 1):
# # #                 formatted_parts.append(
# # #                     f"\n{i}. {src['title']}\n"
# # #                     f"   {src['snippet']}...\n"
# # #                     f"   {src['url']}"
# # #                 )

# # #         formatted_text = "\n".join(formatted_parts) if formatted_parts else f"No results found for: {query}"

# # #         return {
# # #             "query": query,
# # #             "answer": answer,
# # #             "sources": sources,
# # #             "formatted_text": formatted_text
# # #         }

# # #         except Exception as e:
# # #             error = str(e).lower()

# # #             if "rate limit" in error:
# # #                 msg = "Rate limit exceeded. Please try again later."
# # #             elif "authentication" in error or "api key" in error:
# # #                 msg = "Invalid API key. Check your TAVILY_API_KEY."
# # #             elif "network" in error or "connection" in error:
# # #                 msg = "Network error. Check your internet connection."
# # #             else:
# # #                 msg = str(e)

# # #             return {
# # #                 "query": query,
# # #                 "answer": "",
# # #                 "sources": [],
# # #                 "formatted_text": f"Search failed: {msg}",
# # #                 "error": msg
# # #             }



# # # # Test function
# # # def test_search():
# # #     """Test the search tool."""
# # #     try:
# # #         tool = SearchTool()
# # #         result = tool.run("What is Python programming language?", max_results=3)
# # #         print("Search test successful!")
# # #         print(result[:200])
# # #         return True
# # #     except Exception as e:
# # #         print(f"Search test failed: {e}")
# # #         return False


# # # if __name__ == "__main__":
# # #     test_search()

# # def run(self, query: str, max_results: int = 5) -> str:
# #     """Execute search and return formatted text."""
# #     try:
# #         print(f"🔍 Searching: {query[:50]}...")
        
# #         response = self.client.search(
# #             query=query,
# #             max_results=max_results,
# #             search_depth="basic",
# #             include_answer=True,
# #             include_raw_content=False
# #         )
        
# #         # Format results
# #         results = []
        
# #         # Add AI-generated answer if available
# #         if response.get("answer"):
# #             results.append(f"Summary: {response['answer']}")
        
# #         # Add search results
# #         if response.get("results"):
# #             results.append("\nSources:")
# #             for i, result in enumerate(response["results"][:max_results], 1):
# #                 title = result.get("title", "No title")
# #                 content = result.get("content", "")[:200]
# #                 url = result.get("url", "")
                
# #                 results.append(
# #                     f"\n{i}. {title}\n"
# #                     f"   {content}...\n"
# #                     f"   {url}"
# #                 )
        
# #         if not results:
# #             return f"No results found for: {query}"
        
# #         return "\n".join(results)
        
# #     except Exception as e:
# #         # Error handling (same as before)
# #         error_msg = f"Search failed: {str(e)}"
# #         print(f"❌ {error_msg}")
        
# #         if "rate limit" in str(e).lower():
# #             return "Search failed: Rate limit exceeded. Please try again in a moment."
# #         elif "authentication" in str(e).lower() or "api key" in str(e).lower():
# #             return "Search failed: Invalid API key. Check your TAVILY_API_KEY in .env"
# #         elif "network" in str(e).lower() or "connection" in str(e).lower():
# #             return "Search failed: Network error. Check your internet connection."
# #         else:
# #             return f"Search failed: {str(e)}"
# # def test_search():
# #     """Test the search tool."""
# #     try:
# #         tool = SearchTool()
# #         result = tool.run("What is Python programming language?", max_results=3)
# #         print("Search test successful!")
# #         print(result[:200])
# #         return True
# #     except Exception as e:
# #         print(f"Search test failed: {e}")
# #         return False


# # if __name__ == "__main__":
# #     test_search()





# """Tavily search tool with robust error handling."""
# import os
# from dotenv import load_dotenv

# load_dotenv()

# try:
#     from tavily import TavilyClient
#     TAVILY_AVAILABLE = True
# except ImportError:
#     TAVILY_AVAILABLE = False
#     print("Warning: tavily-python not installed. Run: pip install tavily-python")


# class SearchTool:
#     """Web search using Tavily API."""
    
#     def __init__(self):
#         self.api_key = os.getenv("TAVILY_API_KEY")
        
#         if not self.api_key:
#             raise ValueError(
#                 "TAVILY_API_KEY not found in environment. "
#                 "Get one free at: https://tavily.com"
#             )
        
#         if not TAVILY_AVAILABLE:
#             raise ImportError(
#                 "tavily-python not installed. "
#                 "Install with: pip install tavily-python"
#             )
        
#         self.client = TavilyClient(api_key=self.api_key)
    
#     def run(self, query: str, max_results: int = 5) -> str:
#         """Execute search and return formatted text - works for ANY query."""
#         try:
#             print(f"🔍 Searching: {query[:50]}...")
            
#             response = self.client.search(
#                 query=query,
#                 max_results=max_results,
#                 search_depth="basic",
#                 include_answer=True,
#                 include_raw_content=False
#             )
            
#             # Build formatted response
#             output_parts = []
            
#             # 1. AI-generated answer (if available)
#             if response.get("answer"):
#                 output_parts.append(f"Summary: {response['answer']}")
            
#             # 2. Search results with full content
#             results = response.get("results", [])
#             if results:
#                 output_parts.append("\n--- Search Results ---")
                
#                 for i, result in enumerate(results[:max_results], 1):
#                     title = result.get("title", "No title")
#                     content = result.get("content", "No content available")
#                     url = result.get("url", "")
                    
#                     # Format each result
#                     output_parts.append(
#                         f"\n[{i}] {title}\n"
#                         f"{content}\n"
#                         f"Source: {url}"
#                     )
            
#             # 3. Return formatted string
#             if output_parts:
#                 return "\n".join(output_parts)
#             else:
#                 return f"No results found for: {query}"
            
#         except Exception as e:
#             error_msg = str(e)
#             print(f"❌ Search error: {error_msg}")
            
#             # User-friendly error messages
#             if "rate limit" in error_msg.lower():
#                 return "Search failed: Rate limit exceeded. Please try again later."
#             elif "authentication" in error_msg.lower() or "api key" in error_msg.lower():
#                 return "Search failed: Invalid API key. Check your TAVILY_API_KEY."
#             elif "network" in error_msg.lower() or "connection" in error_msg.lower():
#                 return "Search failed: Network error. Check your internet connection."
#             else:
#                 return f"Search failed: {error_msg}"


# def test_search():
#     """Test the search tool."""
#     try:
#         tool = SearchTool()
#         result = tool.run("What is Python programming language?", max_results=3)
#         print("✅ Search test successful!")
#         print(result[:200])
#         return True
#     except Exception as e:
#         print(f"❌ Search test failed: {e}")
#         return False


# if __name__ == "__main__":
#     test_search()

"""Tavily search tool with rich result formatting."""
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    print("Warning: tavily-python not installed. Run: pip install tavily-python")


class SearchTool:
    """Web search using Tavily API with structured output."""
    
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
        """Execute search and return well-formatted results."""
        try:
            print(f"🔍 Searching: {query[:50]}...")
            
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth="basic",
                include_answer=True,
                include_raw_content=False
            )
            
            # Build structured output
            output_parts = []
            
            # Section 1: AI Answer (if available)
            if response.get("answer"):
                output_parts.append("=" * 80)
                output_parts.append("QUICK ANSWER")
                output_parts.append("=" * 80)
                output_parts.append(response["answer"])
                output_parts.append("")
            
            # Section 2: Detailed Results
            results = response.get("results", [])
            if results:
                output_parts.append("=" * 80)
                output_parts.append(f"SEARCH RESULTS ({len(results)} found)")
                output_parts.append("=" * 80)
                
                for i, result in enumerate(results[:max_results], 1):
                    title = result.get("title", "No title")
                    content = result.get("content", "No content available")
                    url = result.get("url", "")
                    
                    # Format each result cleanly
                    output_parts.append(f"\n[Result {i}]")
                    output_parts.append(f"Title: {title}")
                    output_parts.append(f"Content: {content}")
                    output_parts.append(f"Link: {url}")
                    output_parts.append("-" * 80)
            
            # Section 3: Summary footer
            if results:
                output_parts.append(f"\n✓ Found {len(results)} relevant results for: {query}")
            
            # Return formatted text
            if output_parts:
                formatted_output = "\n".join(output_parts)
                print(f"✓ Search completed - {len(results)} results")
                return formatted_output
            else:
                return f"No results found for: {query}"
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Search error: {error_msg}")
            
            # User-friendly error messages
            if "rate limit" in error_msg.lower():
                return "Search failed: Rate limit exceeded. Please try again in a few moments."
            elif "authentication" in error_msg.lower() or "api key" in error_msg.lower():
                return "Search failed: Invalid API key. Check your TAVILY_API_KEY in .env file."
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                return "Search failed: Network error. Check your internet connection."
            else:
                return f"Search failed: {error_msg}"


# Test function
def test_search():
    """Test the search tool with a real query."""
    try:
        tool = SearchTool()
        
        # Test query
        print("\nTesting search with: 'cheap flights Delhi to Bali'\n")
        result = tool.run("cheap flights Delhi to Bali", max_results=3)
        
        print("\n" + "=" * 80)
        print("TEST RESULT")
        print("=" * 80)
        print(result)
        print("=" * 80)
        
        print("\n✅ Search test successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Search test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_search()
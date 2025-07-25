# from .vector_store import ManualVectorStore
# from openai import OpenAI
# import os

# store = ManualVectorStore(os.path.join("ragchat", "data", "parking_manual.txt"))
# client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
# MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# def ask_with_context(question):
#     chunks = store.search(question)
#     context = "\n\n".join(chunks)
#     response = client.chat.completions.create(
#         model=MODEL,
#         messages=[
#             {"role": "system", "content": "You are a helpful assistant for the Smart Parking App user manual. Provide professional, clearly formatted answers."},
#             {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
#         ],
#         max_tokens=500
#     )
#     return response.choices[0].message.content.strip()
from .vector_store import ManualVectorStore
from openai import OpenAI
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ParklyAssistant:
    """
    Enhanced RAG-based assistant for Smart Parking App
    """
    
    def __init__(self, data_path: str = None):
        """
        Initialize the assistant with vector store and OpenAI client
        
        Args:
            data_path: Path to the parking manual data file
        """
        # Setup paths
        if data_path is None:
            data_path = os.path.join("ragchat", "data", "parking_manual.txt")
        
        # Initialize vector store
        try:
            self.store = ManualVectorStore(data_path)
            logger.info(f"Vector store initialized with data from: {data_path}")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
        
        # Initialize OpenAI client
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=api_key)
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        
        # Response configuration
        self.max_tokens = 800
        self.temperature = 0.7
        self.max_chunks = 5  # Limit context chunks for better performance
        
    def _get_system_prompt(self) -> str:
        """
        Generate the system prompt for Parkly Assistant
        """
        return """You are Parkly Sais GPT 🅿️, a friendly and professional assistant for the Smart Parking App.

**Response Guidelines:**
• Be conversational and helpful, like talking to a friend
• Use emojis appropriately to make responses engaging (🚗 🅿️ 📱 ✅ ❌ 💡 📍 ⏰ 💳)
• Structure your answers clearly with numbered steps
• Provide specific examples when helpful
• Always maintain a positive and encouraging tone
• Be honest if you don't have specific information, but remain helpful

**CRITICAL Formatting Rules - MUST FOLLOW:**
• Each numbered step (1., 2., 3., etc.) MUST start on a completely new line
• Put TWO line breaks before each number
• Format like this:

1. First step here

2. Second step here

3. Third step here

• Never put multiple numbers or steps in the same paragraph
• Each step should be complete and clear
• Use simple language
• Each number should be separated clearly from other text"""

    def _format_context(self, chunks: list) -> str:
        """
        Format retrieved chunks into clean context
        
        Args:
            chunks: List of text chunks from vector store
            
        Returns:
            Formatted context string
        """
        if not chunks:
            return "No specific information found in the parking manual."
        
        # Limit chunks and clean them
        limited_chunks = chunks[:self.max_chunks]
        cleaned_chunks = []
        
        for i, chunk in enumerate(limited_chunks, 1):
            # Clean the chunk
            clean_chunk = chunk.strip()
            if clean_chunk:
                cleaned_chunks.append(f"Section {i}:\n{clean_chunk}")
        
        return "\n\n".join(cleaned_chunks)
    
    def _enhance_response(self, response: str) -> str:
        """
        Enhance the response with better formatting and clean structure
        
        Args:
            response: Raw response from OpenAI
            
        Returns:
            Enhanced and formatted response with proper line breaks
        """
        # Clean the response
        enhanced = response.strip()
        
        # Remove any asterisks or complex formatting
        enhanced = enhanced.replace('**', '')
        enhanced = enhanced.replace('*', '')
        
        import re
        
        # CRITICAL: Fix numbered steps - ensure each number starts on completely new line
        # First, add line breaks before any number followed by period
        enhanced = re.sub(r'(\s)(\d+\.)', r'\1\n\n\2', enhanced)
        enhanced = re.sub(r'^(\d+\.)', r'\n\1', enhanced, flags=re.MULTILINE)
        
        # More aggressive: split on numbers anywhere in text
        enhanced = re.sub(r'(\w+)\s+(\d+\.\s+)', r'\1\n\n\2', enhanced)
        
        # Fix cases where numbers come after periods or sentences
        enhanced = re.sub(r'([.!?])\s*(\d+\.)', r'\1\n\n\2', enhanced)
        
        # Fix bullet points - ensure each bullet starts on new line  
        enhanced = re.sub(r'([.!?])\s*•', r'\1\n\n•', enhanced)
        enhanced = re.sub(r'^•', r'\n•', enhanced, flags=re.MULTILINE)
        
        # Clean up multiple newlines but keep double breaks before numbers
        enhanced = re.sub(r'\n{4,}', '\n\n', enhanced)
        
        # Remove any remaining complex formatting
        enhanced = enhanced.replace('##', '')
        enhanced = enhanced.replace('#', '')
        
        # Clean up the start
        enhanced = enhanced.lstrip('\n')
        
        # Add friendly closing if not present
        closing_phrases = [
            'feel free', 'let me know', 'any other', 'help you', 
            'questions', 'need more', 'anything else'
        ]
        
        if not any(phrase in enhanced.lower() for phrase in closing_phrases):
            enhanced += "\n\n💡 Need more help? Feel free to ask! 😊"
        
        return enhanced
    
    def ask_with_context(self, question: str) -> str:
        """
        Process a question with context from the vector store
        
        Args:
            question: User's question about the parking app
            
        Returns:
            Formatted response with context
        """
        try:
            # Validate input
            if not question or not question.strip():
                return "🤔 Please ask me a specific question about the Smart Parking App!"
            
            # Search for relevant context
            logger.info(f"Searching for context: {question[:50]}...")
            chunks = self.store.search(question)
            context = self._format_context(chunks)
            
            # Create the prompt
            user_prompt = f"""Based on the following information about the Smart Parking App:

{context}

Question: {question}

IMPORTANT: When providing step-by-step instructions, format them exactly like this:

Title with emoji

1. First step description

2. Second step description  

3. Third step description

Each number MUST be on its own line with a line break before it. Never put multiple steps in the same paragraph."""

            # Generate response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                presence_penalty=0.1,  # Encourage more diverse responses
                frequency_penalty=0.1   # Reduce repetition
            )
            
            # Extract and enhance the response
            raw_answer = response.choices[0].message.content
            enhanced_answer = self._enhance_response(raw_answer)
            
            logger.info("Response generated successfully")
            return enhanced_answer
            
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            return f"🚫 Sorry, I encountered an error while processing your question. Please try again!\n\nError details: {str(e)}"
    
    def get_quick_help(self) -> str:
        """
        Provide quick help information about the parking app
        """
        return """🅿️ Parkly Assistant - Quick Help

What I can help you with:

• Parking procedures - How to find and book parking spots

• App features - Navigation, payments, notifications  

• Account management - Profile, payment methods, history

• Troubleshooting - Common issues and solutions

• Pricing & policies - Rates, cancellations, refunds

How to ask questions:

• Be specific about what you need help with

• Mention the feature or section you're having trouble with

• Include error messages if you're experiencing issues

Example questions:
• How do I book a parking spot?
• What payment methods are accepted?  
• How do I cancel a reservation?

💡 Ready to help! Ask me anything about the Smart Parking App! 😊"""


# Create global instance for easy import
def initialize_assistant(data_path: str = None) -> ParklyAssistant:
    """
    Initialize and return a ParklyAssistant instance
    
    Args:
        data_path: Optional path to parking manual data
        
    Returns:
        Configured ParklyAssistant instance
    """
    return ParklyAssistant(data_path)


# Backward compatibility function
def ask_with_context(question: str) -> str:
    """
    Backward compatible function for existing code
    
    Args:
        question: User's question
        
    Returns:
        Formatted response
    """
    # Create assistant instance
    assistant = ParklyAssistant()
    return assistant.ask_with_context(question)


# Example usage
if __name__ == "__main__":
    # Initialize assistant
    assistant = ParklyAssistant()
    
    # Example questions
    test_questions = [
        "How do I book a parking spot?",
        "What are the payment options?",
        "How do I cancel my reservation?"
    ]
    
    print("🅿️ Testing Parkly Assistant\n" + "="*50)
    
    for question in test_questions:
        print(f"\n**Question:** {question}")
        print("-" * 30)
        response = assistant.ask_with_context(question)
        print(response)
        print("\n" + "="*50)
import os
import logging

logger = logging.getLogger(__name__)

def format_prompt(chunks, query):
    """
    Formats the retrieved chunks and user query into a prompt for GPT-4.
    """
    context = "\n\n".join([f"- {chunk}" for chunk in chunks])
    return f"""
    As a university teaching assistant, please answer the following question based on the provided context.
    
    Context:
    {context}
    
    Question: {query}
    
    Answer the question based solely on the information provided in the context above.
    If the information isn't available in the context, say so rather than making assumptions.
    Answer:
    """

from openai import OpenAI

def generate_answer_with_gpt(prompt):
    """
    Generates an answer using OpenAI's GPT model with the current API format.
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not found in environment variables")
        
    client = OpenAI(api_key=api_key)
   
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a university teaching assistant. Your responses should be helpful, accurate, and based on the provided course materials."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}", exc_info=True)
        return f"Error generating response: {str(e)}"
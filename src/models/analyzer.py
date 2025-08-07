"""Data analyzer class for OpenAI integration."""

import json
from typing import Any, Dict, List

import openai

from src.utils.dax_utils import clean_dax_query
from src.utils.json_encoder import safe_json_dumps


class DataAnalyzer:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.context = {"tables": [], "schemas": {}, "sample_data": {}}

    def set_data_context(
        self, tables: List[str], schemas: Dict[str, Any], sample_data: Dict[str, List[Dict[str, Any]]]
    ):
        """Set the data context for the analyzer"""
        self.context = {"tables": tables, "schemas": schemas, "sample_data": sample_data}

    def generate_dax_query(self, user_question: str) -> str:
        """Generate a DAX query based on user question"""
        prompt = f"""
        You are a Power BI DAX expert. Generate a DAX query to answer the following question.

        Available tables and their schemas:
        {safe_json_dumps(self.context['schemas'], indent=2)}

        Sample data for reference:
        {safe_json_dumps(self.context['sample_data'], indent=2)}

        User question: {user_question}

        IMPORTANT RULES:
        1. Generate only the DAX query without any explanation
        2. Do NOT use any HTML or XML tags in the query
        3. Do NOT use angle brackets < or > except for DAX operators
        4. Use only valid DAX syntax
        5. Reference only columns that exist in the schema
        6. The query should be executable as-is

        Example format:
        EVALUATE SUMMARIZE(Sales, Product[Category], "Total", SUM(Sales[Amount]))
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a DAX query expert. Generate only valid, clean DAX queries without any markup or formatting.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )

        query = response.choices[0].message.content.strip()
        # Clean any remaining artifacts
        return clean_dax_query(query)

    def interpret_results(self, user_question: str, query_results: List[Dict[str, Any]], dax_query: str) -> str:
        """Interpret query results and provide a natural language answer"""
        prompt = f"""
        You are a data analyst helping users understand their Power BI data.

        User question: {user_question}

        DAX query executed: {dax_query}

        Query results:
        {safe_json_dumps(query_results, indent=2)}

        Provide a clear, concise answer to the user's question based on the results.
        Include relevant numbers and insights. Format the response in a user-friendly way.
        Do not use any HTML or XML markup in your response.
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful data analyst providing insights from Power BI data."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content

    def suggest_questions(self) -> List[str]:
        """Suggest relevant questions based on available data"""
        prompt = f"""
        Based on the following Power BI dataset structure, suggest 5 interesting questions a user might ask:

        Tables and schemas:
        {safe_json_dumps(self.context['schemas'], indent=2)}

        Generate 5 diverse questions that would showcase different aspects of the data.
        Return only the questions as a JSON array.
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data analyst suggesting interesting questions about data."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        try:
            questions = json.loads(response.choices[0].message.content)
            return questions
        except:
            return [
                "What are the total sales?",
                "Show me the top 10 products",
                "What is the trend over time?",
                "Which region has the highest revenue?",
                "What are the key metrics?",
            ]
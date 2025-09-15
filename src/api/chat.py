from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
import re
import logging
from pathlib import Path
import json
import asyncio
from datetime import datetime
import sqlite3

# OpenAI and LangChain imports
try:
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough
    from langchain_community.callbacks import get_openai_callback

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    ChatOpenAI = None

# Configure logging based on environment
debug_mode = os.getenv("DEBUG", "false").lower() == "true"
log_level = logging.DEBUG if debug_mode else logging.WARNING
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    message: str
    conversation_history: List[Dict[str, Any]] = []


class ChatResponse(BaseModel):
    response: str
    is_knowledge_based: bool
    confidence: float = 0.0
    sources_used: List[str] = []
    openai_used: bool = False
    langchain_used: bool = False
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None
    debug_info: Optional[Dict] = None


class KAGOpenAILangChainAgent:
    def __init__(self):
        # Initialize OpenAI and LangChain
        self.setup_llm_clients()

        # Initialize KAG components
        self.db_data = {}  # Changed from csv_data to db_data
        self.knowledge_vectors = None
        self.knowledge_metadata = []
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=2000,
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
        )

        # SQLite database configuration
        self.db_path = self.find_database_file()

        # Load data and build knowledge graph
        self.load_sqlite_data()
        self.build_knowledge_graph()

        # Setup prompts and chains
        self.setup_langchain_components()

        # Debug info
        self.log_initialization_status()

    def find_database_file(self):
        """Find the SQLite database file in possible locations"""
        possible_db_paths = [
            Path("/app/poc_supplychain.db"),  # Docker container path
            Path("poc_supplychain.db"),
            Path("data/poc_supplychain.db"),
            Path("../data/poc_supplychain.db"),
            Path("./app/data/poc_supplychain.db"),
            Path(__file__).parent / "poc_supplychain.db",
            Path(__file__).parent / "data" / "poc_supplychain.db",
            Path(__file__).parent.parent / "poc_supplychain.db",
            Path(__file__).parent.parent / "data" / "poc_supplychain.db",
            Path(__file__).parent.parent.parent / "poc_supplychain.db",
            Path(__file__).parent.parent.parent / "data" / "poc_supplychain.db",
        ]

        for db_path in possible_db_paths:
            logger.debug(f"Checking database path: {db_path}")
            if db_path.exists() and db_path.is_file():
                logger.info(f"Found database file: {db_path}")
                return str(db_path)

        logger.error(
            "Database file 'poc_supplychain.db' not found in any expected location!"
        )
        logger.info("Searched paths:")
        for db_path in possible_db_paths:
            logger.info(f"  - {db_path} (exists: {db_path.exists()})")

        return None

    def get_database_schema(self):
        """Get all table names and their schemas from the SQLite database"""
        if not self.db_path:
            logger.error("No database path available")
            return {}

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get all table names
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()

                schema_info = {}
                for (table_name,) in tables:
                    # Skip SQLite internal tables
                    if table_name.startswith("sqlite_"):
                        continue

                    # Get column information
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()

                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]

                    schema_info[table_name] = {
                        "columns": [
                            (col[1], col[2]) for col in columns
                        ],  # (name, type)
                        "row_count": row_count,
                    }

                    logger.info(
                        f"Table '{table_name}': {len(columns)} columns, {row_count} rows"
                    )

                return schema_info

        except Exception as e:
            logger.error(f"Error getting database schema: {e}")
            return {}

    def load_sqlite_data(self):
        """Load data from SQLite database tables into pandas DataFrames"""
        if not self.db_path:
            logger.error("No database file found!")
            return

        try:
            # Get schema information first
            schema = self.get_database_schema()
            logger.info(f"Database contains {len(schema)} tables")

            with sqlite3.connect(self.db_path) as conn:
                for table_name, table_info in schema.items():
                    try:
                        # Load table data into DataFrame
                        query = f"SELECT * FROM {table_name}"
                        df = pd.read_sql_query(query, conn)

                        # Clean column names
                        df.columns = df.columns.str.strip()

                        # Store with cleaned name
                        clean_table_name = table_name.lower().replace(" ", "_")
                        self.db_data[clean_table_name] = df

                        logger.info(
                            f"Loaded table '{table_name}': {len(df)} rows, {len(df.columns)} columns"
                        )
                        logger.debug(f"Columns: {list(df.columns)}")

                        # Log sample data for debugging
                        if len(df) > 0:
                            logger.debug(
                                f"Sample row from {table_name}: {df.iloc[0].to_dict()}"
                            )

                    except Exception as e:
                        logger.error(f"Error loading table {table_name}: {e}")

        except Exception as e:
            logger.error(f"Error connecting to database: {e}")

    def execute_custom_query(self, query: str) -> pd.DataFrame:
        """Execute a custom SQL query and return results as DataFrame"""
        if not self.db_path:
            logger.error("No database path available")
            return pd.DataFrame()

        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn)
                logger.info(f"Custom query executed: {len(df)} rows returned")
                return df
        except Exception as e:
            logger.error(f"Error executing custom query: {e}")
            return pd.DataFrame()

    def log_initialization_status(self):
        """Log detailed initialization status for debugging"""
        logger.info("=== KAG AGENT INITIALIZATION STATUS ===")
        logger.info(f"Database path: {self.db_path}")
        logger.info(f"Database tables loaded: {len(self.db_data)}")

        for table_name, df in self.db_data.items():
            logger.info(
                f"  - {table_name}: {len(df)} rows, columns: {list(df.columns)}"
            )

        logger.info(f"Knowledge vectors built: {self.knowledge_vectors is not None}")
        if self.knowledge_vectors is not None:
            logger.info(f"Knowledge entries: {len(self.knowledge_metadata)}")

        logger.info(
            f"OpenAI client: {'Available' if self.openai_client else 'Not available'}"
        )
        logger.info(
            f"LangChain client: {'Available' if self.langchain_llm else 'Not available'}"
        )
        logger.info("==========================================")

    def setup_llm_clients(self):
        """Setup both OpenAI and LangChain clients with better error handling"""
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment variables!")

        # OpenAI Direct Client
        if OPENAI_AVAILABLE and api_key:
            try:
                self.openai_client = AsyncOpenAI(api_key=api_key)
                logger.info("OpenAI direct client initialized")
            except Exception as e:
                logger.error(f"OpenAI direct client failed: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
            logger.warning("OpenAI direct client not available")

        # LangChain Client
        if LANGCHAIN_AVAILABLE and api_key:
            try:
                self.langchain_llm = ChatOpenAI(
                    api_key=api_key,
                    model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                    temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.3")),
                    max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "1500")),
                    streaming=False,
                )
                logger.info("LangChain OpenAI client initialized")
            except Exception as e:
                logger.error(f"LangChain client failed: {e}")
                self.langchain_llm = None
        else:
            self.langchain_llm = None
            logger.warning("LangChain client not available")

    def setup_langchain_components(self):
        """Setup LangChain prompts and chains with enhanced prompts"""
        if not self.langchain_llm:
            self.langchain_chains = {}
            return

        # Enhanced knowledge-based analysis chain
        knowledge_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a specialized supply chain management AI assistant with access to real-time database data.

CRITICAL INSTRUCTIONS:
1. ALWAYS use the provided database context to answer questions
2. For inventory/stock queries, provide SPECIFIC details from the data
3. Format responses professionally with clear structure
4. Use appropriate formatting for supply chain management
5. Always cite which database tables you're referencing

RESPONSE GUIDELINES:
- For "low stock" queries: List ALL items with stock levels below threshold, highlight critical items
- For "total count" queries: Count and list the exact numbers from the database data
- For general queries: Provide specific insights based on actual database records
- Always mention specific item names, stock levels, suppliers when available

DATABASE CONTEXT PROVIDED:
{context}

Remember: You have access to real supply chain database data. Use it to provide specific, actionable insights.""",
                ),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{query}"),
            ]
        )

        # Enhanced analytics chain
        analytics_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a supply chain data analyst with access to comprehensive database information.

ANALYSIS REQUIREMENTS:
1. Perform detailed quantitative analysis of the provided database data
2. Calculate specific metrics (totals, averages, percentages)
3. Identify trends and patterns in the supply chain data
4. Provide actionable recommendations based on data insights
5. Present findings in structured format with specific numbers

DATA ANALYSIS FOCUS:
- Stock levels and reorder points
- Supplier performance and pricing
- Product categories and classifications
- Critical stock alerts and recommendations

DATABASE CONTEXT:
{context}""",
                ),
                MessagesPlaceholder(variable_name="history"),
                ("human", "Perform detailed analysis for: {query}"),
            ]
        )

        # Fallback general chain
        general_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a supply chain management AI assistant.

If you have database context, use it to provide specific answers.
If no data context is available, explain what information you would need and suggest specific questions.

Guidelines:
- Be helpful and professional
- Focus on supply chain management
- Provide practical advice
- If you have data, use specific examples from it""",
                ),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{query}"),
            ]
        )

        # Create chains
        self.langchain_chains = {
            "knowledge": knowledge_prompt | self.langchain_llm | StrOutputParser(),
            "analytics": analytics_prompt | self.langchain_llm | StrOutputParser(),
            "general": general_prompt | self.langchain_llm | StrOutputParser(),
        }

        logger.info("Enhanced LangChain chains initialized")

    def build_knowledge_graph(self):
        """Enhanced knowledge graph building with database data"""
        all_text_data = []
        self.knowledge_metadata = []

        if not self.db_data:
            logger.error("No database data available for knowledge graph building")
            return

        for table_name, df in self.db_data.items():
            logger.info(f"Processing {table_name} with {len(df)} rows")

            for idx, row in df.iterrows():
                try:
                    row_text = self.create_enhanced_text_representation(table_name, row)
                    all_text_data.append(row_text)

                    # Store comprehensive metadata
                    metadata = {
                        "table": table_name,
                        "row_index": idx,
                        "data": row.to_dict(),
                        "text_representation": row_text,
                        "searchable_fields": self.extract_searchable_fields(row),
                    }
                    self.knowledge_metadata.append(metadata)

                except Exception as e:
                    logger.error(f"Error processing row {idx} in {table_name}: {e}")

        if all_text_data:
            try:
                self.knowledge_vectors = self.vectorizer.fit_transform(all_text_data)
                logger.info(f"Built knowledge graph with {len(all_text_data)} entries")
                logger.debug(f"Vocabulary size: {len(self.vectorizer.vocabulary_)}")

            except Exception as e:
                logger.error(f"Error building knowledge vectors: {e}")
                self.knowledge_vectors = None
        else:
            logger.error("No text data available for vectorization")

    def extract_searchable_fields(self, row):
        """Extract key searchable fields for better matching"""
        searchable = {}

        for col, val in row.items():
            if pd.notna(val):
                col_lower = col.lower()

                # Categorize important fields for supply chain
                if any(
                    keyword in col_lower
                    for keyword in ["name", "product", "item", "material", "part"]
                ):
                    searchable["item_name"] = str(val)
                elif any(
                    keyword in col_lower
                    for keyword in ["stock", "quantity", "inventory", "current"]
                ):
                    searchable["stock_level"] = val
                elif any(
                    keyword in col_lower
                    for keyword in ["supplier", "vendor", "manufacturer"]
                ):
                    searchable["supplier"] = str(val)
                elif any(
                    keyword in col_lower for keyword in ["price", "cost", "value"]
                ):
                    searchable["price"] = val
                elif any(
                    keyword in col_lower for keyword in ["status", "alert", "condition"]
                ):
                    searchable["status"] = str(val)
                elif any(
                    keyword in col_lower for keyword in ["category", "type", "class"]
                ):
                    searchable["category"] = str(val)

        return searchable

    def create_enhanced_text_representation(self, table_name, row):
        """Create enhanced text representation for database records"""
        # Emphasize table name for better matching
        text_parts = [
            f"table {table_name}",
            f"table_{table_name}",
            table_name,
            table_name.replace("_", " "),
            f"from {table_name} table",
            f"database table {table_name}"
        ]

        # Add all field information
        for col, val in row.items():
            if pd.notna(val) and str(val).strip():
                col_clean = col.lower().replace("_", " ")
                text_parts.append(f"{col_clean} {val}")

                # Add contextual keywords for better matching
                if any(
                    keyword in col_clean
                    for keyword in ["stock", "quantity", "inventory", "current"]
                ):
                    try:
                        val_num = float(val)
                        if val_num < 5:
                            text_parts.extend(
                                [
                                    "critical stock shortage",
                                    "urgent reorder needed",
                                    "very low inventory",
                                    "stock emergency",
                                ]
                            )
                        elif val_num < 10:
                            text_parts.extend(
                                [
                                    "critical low stock",
                                    "immediate attention needed",
                                    "reorder urgently",
                                ]
                            )
                        elif val_num < 25:
                            text_parts.extend(
                                ["low stock alert", "reorder soon", "stock running low"]
                            )
                        elif val_num < 50:
                            text_parts.extend(
                                [
                                    "moderate stock level",
                                    "monitor inventory",
                                    "consider reordering",
                                ]
                            )
                        else:
                            text_parts.extend(
                                [
                                    "adequate stock",
                                    "sufficient inventory",
                                    "good stock level",
                                ]
                            )
                    except ValueError:
                        pass

                # Add supply chain related keywords
                if any(
                    keyword in col_clean
                    for keyword in ["product", "item", "material", "part"]
                ):
                    text_parts.extend(
                        [
                            "supply chain item",
                            "inventory product",
                            "stock item",
                            "supply chain product",
                        ]
                    )

        return " ".join(text_parts)

    def detect_direct_table_query(self, query: str) -> Optional[List[str]]:
        """Detect if user is asking about specific database tables"""
        query_lower = query.lower()

        # Known table names from the database
        available_tables = list(self.db_data.keys())
        mentioned_tables = []

        # Check for direct table name mentions
        for table in available_tables:
            # Check various forms of the table name
            table_variations = [
                table,
                table.replace("_", " "),
                table.replace("_", ""),
                table.rstrip("s"),  # Remove plural
                table + "s"  # Add plural
            ]

            for variation in table_variations:
                if variation in query_lower:
                    mentioned_tables.append(table)
                    break

        # Check for general table queries
        if any(phrase in query_lower for phrase in ["what tables", "show tables", "list tables", "database schema"]):
            return available_tables

        return mentioned_tables if mentioned_tables else None

    def detect_query_intent(self, query: str) -> Dict[str, Any]:
        """Enhanced query intent detection for supply chain queries"""
        query_lower = query.lower().strip()

        # First check for direct table queries
        direct_tables = self.detect_direct_table_query(query)
        if direct_tables:
            logger.info(f"Direct table query detected: {direct_tables}")

        # Supply chain specific intent patterns
        intent_patterns = {
            "low_stock_query": [
                r"\b(low|critical|out of|running low|shortage|depleted)\b.*\b(stock|inventory|item|product)\b",
                r"\b(stock|inventory)\s+(level|status|alert|low|critical)\b",
                r"\b(reorder|replenish|refill)\b",
                r"\b(give me|show me|list|find)\b.*\b(low stock|low inventory)\b",
            ],
            "count_query": [
                r"\b(how many|count|total|number of)\b.*\b(item|product|supplier|order)\b",
                r"\b(total|count)\b.*\b(inventory|stock|products)\b",
            ],
            "search_items": [
                r"\b(find|search|show|list|get|give me)\b.*\b(item|product|supplier|order)\b",
                r"\b(which|what)\s+(items|products|suppliers)\b",
            ],
            "analytics": [
                r"\b(analyze|analysis|report|statistics|trend|insights|patterns|summary)\b",
                r"\b(dashboard|overview|status report)\b",
            ],
            "pricing": [r"\b(price|cost|expensive|cheap|pricing|budget)\b"],
            "supplier": [r"\b(supplier|vendor|manufacturer|distributor)\b"],
            "orders": [r"\b(order|purchase|procurement|delivery)\b"],
        }

        detected_intents = []
        intent_confidence = 0.0
        primary_intent = "general"

        # Check for specific patterns
        for intent_type, patterns in intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    detected_intents.append(intent_type)
                    intent_confidence += 0.3
                    if primary_intent == "general":
                        primary_intent = intent_type
                    break

        # Special handling for common queries
        if any(
            phrase in query_lower for phrase in ["low stock", "running low", "shortage"]
        ):
            primary_intent = "low_stock_query"
            intent_confidence = max(intent_confidence, 0.9)

        if any(phrase in query_lower for phrase in ["how many", "total", "count"]):
            primary_intent = "count_query"
            intent_confidence = max(intent_confidence, 0.9)

        # Determine if this requires knowledge retrieval
        is_knowledge_query = len(detected_intents) > 0 or any(
            keyword in query_lower
            for keyword in [
                "inventory",
                "stock",
                "product",
                "item",
                "supplier",
                "low",
                "critical",
                "show",
                "find",
                "list",
                "how many",
                "total",
                "count",
                "price",
                "order",
            ]
        )

        # Choose processing approach
        use_langchain = is_knowledge_query and self.langchain_llm is not None

        chain_type = (
            "analytics"
            if "analytics" in detected_intents
            else ("knowledge" if is_knowledge_query else "general")
        )

        result = {
            "is_knowledge_query": is_knowledge_query,
            "confidence": min(intent_confidence, 1.0) if is_knowledge_query else 0.0,
            "detected_intents": detected_intents,
            "primary_intent": primary_intent,
            "query_lower": query_lower,
            "use_langchain": use_langchain,
            "chain_type": chain_type,
            "direct_tables": direct_tables,
        }

        logger.debug(f"Intent detection result: {result}")
        return result

    def retrieve_direct_table_data(self, table_names: List[str], limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve data directly from specified tables"""
        results = []

        for table_name in table_names:
            if table_name in self.db_data:
                df = self.db_data[table_name]

                # Get sample rows from the table
                sample_df = df.head(limit) if len(df) > limit else df

                for idx, row in sample_df.iterrows():
                    result = {
                        "metadata": {
                            "table": table_name,
                            "row_index": idx,
                            "data": row.to_dict(),
                            "searchable_fields": self.extract_searchable_fields(row),
                        },
                        "similarity": 1.0,  # Perfect match for direct queries
                        "content": self.get_structured_content({
                            "table": table_name,
                            "data": row.to_dict(),
                            "searchable_fields": self.extract_searchable_fields(row),
                        })
                    }
                    results.append(result)

                logger.info(f"Retrieved {len(sample_df)} records from table '{table_name}'")
            else:
                logger.warning(f"Table '{table_name}' not found in database")

        return results

    def retrieve_knowledge(self, query: str, top_k: int = 15, intent: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Enhanced knowledge retrieval with database data"""
        # Check for direct table queries first
        if intent and intent.get("direct_tables"):
            logger.info(f"Using direct table retrieval for tables: {intent['direct_tables']}")
            return self.retrieve_direct_table_data(intent["direct_tables"], limit=top_k)

        if not hasattr(self, "knowledge_vectors") or self.knowledge_vectors is None:
            logger.error("Knowledge vectors not available for retrieval")
            return []

        try:
            # Create enhanced query for better matching
            enhanced_query = self.enhance_query(query)
            logger.debug(f"Enhanced query: {enhanced_query}")

            # Get similarities
            query_vector = self.vectorizer.transform([enhanced_query])
            similarities = cosine_similarity(
                query_vector, self.knowledge_vectors
            ).flatten()

            # Use lower threshold for better matching
            threshold = float(os.getenv("KNOWLEDGE_SIMILARITY_THRESHOLD", "0.001"))
            valid_indices = np.where(similarities > threshold)[0]

            logger.debug(
                f"Found {len(valid_indices)} matches above threshold {threshold}"
            )

            if len(valid_indices) == 0:
                logger.warning("No matches found, returning top results anyway")
                top_indices = np.argsort(similarities)[-top_k:][::-1]
                valid_indices = top_indices

            # Sort by similarity and get top results
            valid_similarities = similarities[valid_indices]
            sorted_indices = np.argsort(valid_similarities)[-top_k:][::-1]
            top_valid_indices = valid_indices[sorted_indices]

            results = []
            for idx in top_valid_indices:
                try:
                    result = {
                        "metadata": self.knowledge_metadata[idx],
                        "similarity": float(similarities[idx]),
                        "content": self.get_structured_content(
                            self.knowledge_metadata[idx]
                        ),
                    }
                    results.append(result)

                    logger.debug(
                        f"Retrieved: {self.knowledge_metadata[idx]['table']} - similarity: {similarities[idx]:.3f}"
                    )

                except Exception as e:
                    logger.error(f"Error processing result {idx}: {e}")

            logger.info(
                f"Retrieved {len(results)} knowledge items for query: '{query}'"
            )
            return results

        except Exception as e:
            logger.error(f"Error in knowledge retrieval: {e}")
            return []

    def enhance_query(self, query: str) -> str:
        """Enhanced query with supply chain specific synonyms"""
        query_lower = query.lower()
        enhanced_terms = [query_lower]

        # Supply chain specific synonyms
        synonyms = {
            "low stock": [
                "low inventory",
                "stock shortage",
                "running low",
                "critical stock",
                "reorder level",
                "depleted stock",
                "insufficient inventory",
                "stock alert",
                "inventory warning",
                "shortage alert",
            ],
            "product": [
                "item",
                "material",
                "part",
                "component",
                "goods",
                "merchandise",
                "supply",
                "inventory item",
                "stock item",
                "medications",
                "medicine",
            ],
            "find": ["search", "show", "list", "get", "locate", "identify", "display"],
            "total": ["count", "number", "sum", "amount", "quantity"],
            "price": ["cost", "pricing", "rate", "expense", "value", "amount"],
            "supplier": ["vendor", "provider", "distributor", "manufacturer", "suppliers"],
            "order": ["purchase order", "po", "procurement", "purchase_orders"],
            "inventory": ["stock", "warehouse", "storage", "consumption_history"],
        }

        # Add table name variations
        for table_name in self.db_data.keys():
            table_clean = table_name.replace("_", " ")
            enhanced_terms.extend([table_name, table_clean, f"table {table_name}"])

        for term, syns in synonyms.items():
            if term in query_lower:
                enhanced_terms.extend(syns)

        # Add context-specific terms
        if any(word in query_lower for word in ["how many", "total", "count"]):
            enhanced_terms.extend(
                ["inventory count", "stock total", "product quantity"]
            )

        return " ".join(enhanced_terms)

    def get_structured_content(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Get structured content for LLM processing"""
        return {
            "table": metadata["table"],
            "data": metadata["data"],
            "searchable_fields": metadata.get("searchable_fields", {}),
            "context": f"Record from {metadata['table']} database table",
        }

    def prepare_context_for_llm(self, knowledge_context: List[Dict[str, Any]]) -> str:
        """Enhanced context preparation with database data organization"""
        if not knowledge_context:
            return "No database context available."

        # Group by table for better organization
        tables_data = {}
        for item in knowledge_context:
            table = item["metadata"]["table"]
            if table not in tables_data:
                tables_data[table] = []
            tables_data[table].append(
                {
                    "data": item["metadata"]["data"],
                    "similarity": item["similarity"],
                    "searchable_fields": item["metadata"].get("searchable_fields", {}),
                }
            )

        context_parts = []
        context_parts.append("**SUPPLY CHAIN DATABASE DATA:**\n")

        total_records = 0
        for table_name, rows in tables_data.items():
            context_parts.append(f"**{table_name.upper().replace('_', ' ')} TABLE:**")

            if rows:
                # Show key columns first
                sample_row = rows[0]["data"]
                important_columns = []
                other_columns = []

                for col in sample_row.keys():
                    col_lower = col.lower()
                    if any(
                        key in col_lower
                        for key in [
                            "name",
                            "product",
                            "item",
                            "stock",
                            "quantity",
                            "price",
                            "supplier",
                            "status",
                            "alert",
                            "category",
                        ]
                    ):
                        important_columns.append(col)
                    else:
                        other_columns.append(col)

                all_columns = important_columns + other_columns
                context_parts.append(f"Key Columns: {', '.join(all_columns[:8])}")

                # Show detailed data for top matches
                for i, row_info in enumerate(rows[:10]):
                    row_data = row_info["data"]
                    similarity = row_info["similarity"]

                    important_data = []
                    for col in all_columns[:6]:
                        if col in row_data:
                            value = row_data[col]
                            if pd.notna(value) and str(value).strip():
                                # Format specific field types
                                if any(
                                    keyword in col.lower()
                                    for keyword in ["stock", "quantity"]
                                ):
                                    try:
                                        val_num = float(value)
                                        status = ""
                                        if val_num < 10:
                                            status = " CRITICAL LOW"
                                        elif val_num < 25:
                                            status = " LOW"
                                        important_data.append(f"{col}: {value}{status}")
                                    except ValueError:
                                        important_data.append(f"{col}: {value}")
                                else:
                                    important_data.append(f"{col}: {value}")

                    if important_data:
                        context_parts.append(
                            f"Record {i + 1}: {' | '.join(important_data)} (match: {similarity:.2f})"
                        )

                if len(rows) > 10:
                    context_parts.append(
                        f"... and {len(rows) - 10} more matching records"
                    )

                total_records += len(rows)

            context_parts.append("")

        context_parts.append(
            f"**SUMMARY:** {len(tables_data)} table(s), {total_records} matching records"
        )
        context_parts.append(
            "\n**INSTRUCTION:** Use this specific database data to answer the user's question with exact details, numbers, and item names."
        )

        final_context = "\n".join(context_parts)
        logger.debug(f"Prepared context length: {len(final_context)} characters")

        return final_context

    def convert_history_to_messages(
        self, conversation_history: List[Dict] = None
    ) -> List:
        """Convert conversation history to LangChain message format"""
        if not conversation_history:
            return []

        messages = []
        for msg in conversation_history[-5:]:
            try:
                role = msg.get("role", "user")
                content = msg.get("content", "").strip()

                if content:
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))
            except Exception as e:
                logger.error(f"Error processing history message: {e}")

        return messages

    async def generate_langchain_response(
        self,
        query: str,
        knowledge_context: List[Dict[str, Any]],
        intent: Dict[str, Any],
        conversation_history: List[Dict] = None,
    ) -> Dict[str, Any]:
        """Generate response using LangChain with enhanced error handling"""
        if not self.langchain_llm or not self.langchain_chains:
            logger.warning("LangChain not available, falling back to OpenAI direct")
            return await self.generate_openai_direct_response(
                query, knowledge_context, intent, conversation_history
            )

        try:
            # Prepare context and history
            context = self.prepare_context_for_llm(knowledge_context)
            history = self.convert_history_to_messages(conversation_history)

            # Choose appropriate chain
            chain_type = intent.get("chain_type", "knowledge")
            chain = self.langchain_chains.get(
                chain_type, self.langchain_chains["knowledge"]
            )

            logger.info(f"Using LangChain chain: {chain_type}")
            logger.debug(
                f"Context length: {len(context)} chars, History: {len(history)} messages"
            )

            # Track costs and tokens
            with get_openai_callback() as cb:
                if chain_type in ["knowledge", "analytics"]:
                    response = await chain.ainvoke(
                        {"query": query, "context": context, "history": history}
                    )
                else:
                    response = await chain.ainvoke({"query": query, "history": history})

            logger.info(
                f"LangChain response generated. Tokens: {cb.total_tokens}, Cost: ${cb.total_cost}"
            )

            return {
                "response": response,
                "langchain_used": True,
                "openai_used": False,
                "tokens_used": cb.total_tokens,
                "cost_estimate": cb.total_cost,
                "sources_used": [
                    item["metadata"]["table"] for item in knowledge_context
                ],
                "chain_used": chain_type,
            }

        except Exception as e:
            logger.error(f"LangChain error: {e}")
            return await self.generate_openai_direct_response(
                query, knowledge_context, intent, conversation_history
            )

    async def generate_openai_direct_response(
        self,
        query: str,
        knowledge_context: List[Dict[str, Any]],
        intent: Dict[str, Any],
        conversation_history: List[Dict] = None,
    ) -> Dict[str, Any]:
        """Enhanced direct OpenAI API with better prompting"""
        if not self.openai_client:
            logger.warning("OpenAI client not available, generating fallback response")
            return {
                "response": self.generate_fallback_response(knowledge_context),
                "langchain_used": False,
                "openai_used": False,
            }

        try:
            context = self.prepare_context_for_llm(knowledge_context)

            # Enhanced system prompt based on intent
            if intent.get("primary_intent") == "low_stock_query":
                system_prompt = """You are a supply chain inventory specialist. The user is asking about low stock items.

CRITICAL INSTRUCTIONS:
1. Analyze the provided database data carefully
2. Identify ALL items with stock levels below 50 units
3. Highlight CRITICAL items (stock < 10 units) with alerts
4. List specific item names, current stock levels, and suppliers
5. Provide actionable recommendations for reordering
6. Use professional formatting with bullet points

Format your response as:
CRITICAL LOW STOCK (< 10 units):
- [Item Name]: [Current Stock] units - Supplier: [Supplier] - ACTION: ORDER IMMEDIATELY

LOW STOCK ALERTS (< 50 units):  
- [Item Name]: [Current Stock] units - Supplier: [Supplier] - ACTION: Monitor closely

If no low stock items found, clearly state "All inventory levels are adequate" and provide a summary of stock status."""

            elif intent.get("primary_intent") == "count_query":
                system_prompt = """You are a supply chain data analyst. The user wants to know quantities/counts.

CRITICAL INSTRUCTIONS:
1. Count the EXACT number of items from the provided data
2. Provide specific numbers, not estimates
3. Break down by categories if relevant (tables, suppliers, etc.)
4. Show the calculation clearly
5. Use structured formatting with clear totals

Format your response as:
INVENTORY COUNT SUMMARY:
• Total Items: [EXACT NUMBER]
• By Category: [breakdown if available]
• Data Sources: [list tables used]

Always provide the specific count based on the actual data provided."""

            else:
                system_prompt = """You are a specialized supply chain management AI assistant with access to real-time database data.

CRITICAL INSTRUCTIONS:
1. Use the provided database data to give specific, accurate answers
2. Reference actual item names, stock levels, suppliers from the data
3. Provide actionable insights based on the real data
4. Use professional formatting
5. Always cite which data you're using

If you have database data, use it extensively. If no relevant data is provided, explain what information you need."""

            # Build messages with context
            messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-3:]:
                    role = "user" if msg.get("role") == "user" else "assistant"
                    content = msg.get("content", "").strip()
                    if content:
                        messages.append({"role": role, "content": content})

            # Add current query with context
            user_message = f"""USER QUERY: {query}

DATABASE CONTEXT:
{context}

Please provide a detailed, specific response based on this database data."""

            messages.append({"role": "user", "content": user_message})

            logger.info(f"Sending request to OpenAI with {len(messages)} messages")

            response = await self.openai_client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                messages=messages,
                max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "1500")),
                temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.3")),
            )

            logger.info(f"OpenAI direct response generated")

            return {
                "response": response.choices[0].message.content,
                "langchain_used": False,
                "openai_used": True,
                "tokens_used": response.usage.total_tokens
                if hasattr(response, "usage")
                else None,
                "sources_used": [
                    item["metadata"]["table"] for item in knowledge_context
                ],
            }

        except Exception as e:
            logger.error(f"OpenAI direct API error: {e}")
            return {
                "response": self.generate_fallback_response(knowledge_context),
                "langchain_used": False,
                "openai_used": False,
                "error": str(e),
            }

    def generate_fallback_response(
        self, knowledge_context: List[Dict[str, Any]]
    ) -> str:
        """Enhanced fallback response with actual data analysis"""
        if not knowledge_context:
            return """Unable to process your query due to API configuration issues.
            
Troubleshooting Steps:
1. Check if OPENAI_API_KEY is set in environment variables
2. Verify API key has sufficient credits
3. Ensure database is loaded correctly

Please check your API configuration and try again."""

        # Analyze the data directly without LLM
        response_parts = ["DATABASE DATA ANALYSIS (Fallback Mode)\n"]

        # Group data by table
        tables_data = {}
        for item in knowledge_context:
            table = item["metadata"]["table"]
            if table not in tables_data:
                tables_data[table] = []
            tables_data[table].append(item["metadata"]["data"])

        total_items = 0
        low_stock_items = []
        critical_stock_items = []

        for table_name, rows in tables_data.items():
            response_parts.append(f"**{table_name.upper().replace('_', ' ')}:**")

            table_count = len(rows)
            total_items += table_count
            response_parts.append(f"• Total items: {table_count}")

            # Analyze stock levels if available
            for row in rows:
                item_name = "Unknown"
                current_stock = None
                supplier = "Unknown"

                # Extract key information
                for key, value in row.items():
                    if pd.notna(value):
                        key_lower = key.lower()
                        if any(
                            name_key in key_lower
                            for name_key in ["name", "product", "item"]
                        ):
                            item_name = str(value)
                        elif any(
                            stock_key in key_lower
                            for stock_key in ["stock", "quantity", "current"]
                        ):
                            try:
                                current_stock = float(value)
                            except ValueError:
                                pass
                        elif any(
                            supplier_key in key_lower
                            for supplier_key in ["supplier", "vendor"]
                        ):
                            supplier = str(value)

                # Categorize by stock level
                if current_stock is not None:
                    if current_stock < 10:
                        critical_stock_items.append(
                            f"CRITICAL: {item_name}: {current_stock} units (Supplier: {supplier})"
                        )
                    elif current_stock < 50:
                        low_stock_items.append(
                            f"LOW: {item_name}: {current_stock} units (Supplier: {supplier})"
                        )

            response_parts.append("")

        # Summary section
        response_parts.append(f"**SUMMARY:**")
        response_parts.append(f"• Total inventory items: {total_items}")
        response_parts.append(f"• Data sources: {len(tables_data)} table(s)")

        if critical_stock_items:
            response_parts.append(
                f"\n**CRITICAL LOW STOCK** ({len(critical_stock_items)} items):"
            )
            for item in critical_stock_items:
                response_parts.append(f"  {item}")

        if low_stock_items:
            response_parts.append(
                f"\n**LOW STOCK ALERTS** ({len(low_stock_items)} items):"
            )
            for item in low_stock_items:
                response_parts.append(f"  {item}")

        if not critical_stock_items and not low_stock_items:
            response_parts.append(
                "\n**STOCK STATUS:** All items appear to have adequate stock levels"
            )

        response_parts.append(
            f"\n*Note: Enhanced AI analysis unavailable. API configuration needed for detailed insights.*"
        )

        return "\n".join(response_parts)

    async def process_chat(
        self, message: str, conversation_history: List[Dict] = None
    ) -> ChatResponse:
        """Enhanced main chat processing with comprehensive debugging"""
        try:
            logger.info(f"Processing query: '{message}'")

            # Detect query intent
            intent = self.detect_query_intent(message)
            logger.info(
                f"Intent detected: {intent['primary_intent']} (confidence: {intent['confidence']:.2f})"
            )

            # Retrieve knowledge if needed
            knowledge = []
            debug_info = {
                "intent": intent,
                "knowledge_retrieved": 0,
                "processing_method": "none",
            }

            if intent["is_knowledge_query"]:
                knowledge = self.retrieve_knowledge(message, top_k=20, intent=intent)
                debug_info["knowledge_retrieved"] = len(knowledge)
                logger.info(f"Retrieved {len(knowledge)} knowledge items")

                # Log knowledge summary for debugging
                if knowledge:
                    tables_found = set(item["metadata"]["table"] for item in knowledge)
                    logger.info(f"Knowledge from tables: {list(tables_found)}")
            else:
                logger.info("Query not identified as knowledge-based")

            # Choose processing approach
            result = None
            if intent["use_langchain"] and self.langchain_llm:
                debug_info["processing_method"] = "langchain"
                logger.info("Using LangChain processing")
                result = await self.generate_langchain_response(
                    message, knowledge, intent, conversation_history
                )
            elif self.openai_client:
                debug_info["processing_method"] = "openai_direct"
                logger.info("Using OpenAI direct processing")
                result = await self.generate_openai_direct_response(
                    message, knowledge, intent, conversation_history
                )
            else:
                debug_info["processing_method"] = "fallback"
                logger.info("Using fallback processing")
                result = {
                    "response": self.generate_fallback_response(knowledge),
                    "langchain_used": False,
                    "openai_used": False,
                }

            if result is None:
                raise Exception("No processing method succeeded")

            # Prepare final response
            confidence = max(
                intent["confidence"], 0.8 if knowledge and len(knowledge) > 5 else 0.3
            )

            response = ChatResponse(
                response=result["response"],
                is_knowledge_based=intent["is_knowledge_query"],
                confidence=confidence,
                sources_used=result.get("sources_used", []),
                openai_used=result.get("openai_used", False),
                langchain_used=result.get("langchain_used", False),
                tokens_used=result.get("tokens_used"),
                cost_estimate=result.get("cost_estimate"),
                debug_info=debug_info,
            )

            logger.info(
                f"Response generated successfully (method: {debug_info['processing_method']})"
            )
            return response

        except Exception as e:
            logger.error(f"Error processing chat: {e}", exc_info=True)
            return ChatResponse(
                response=f"I encountered an error processing your request: {str(e)}. Please check the system configuration and try again.",
                is_knowledge_based=False,
                confidence=0.0,
                debug_info={"error": str(e)},
            )


# Initialize the enhanced agent
kag_openai_langchain_agent = KAGOpenAILangChainAgent()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatMessage):
    """Enhanced KAG + OpenAI + LangChain Chat endpoint"""
    try:
        response = await kag_openai_langchain_agent.process_chat(
            chat_request.message, chat_request.conversation_history
        )
        return response
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/chat/system-status")
async def get_system_status():
    """Get comprehensive system status and capabilities"""
    try:
        # Test knowledge retrieval
        test_query = "low stock items"
        test_knowledge = kag_openai_langchain_agent.retrieve_knowledge(
            test_query, top_k=5
        )

        return {
            "system_health": "Healthy",
            "openai_direct_available": kag_openai_langchain_agent.openai_client
            is not None,
            "langchain_available": kag_openai_langchain_agent.langchain_llm is not None,
            "openai_package_installed": OPENAI_AVAILABLE,
            "langchain_package_installed": LANGCHAIN_AVAILABLE,
            "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
            "knowledge_base": {
                "total_tables": len(kag_openai_langchain_agent.db_data),
                "table_names": list(kag_openai_langchain_agent.db_data.keys()),
                "total_records": sum(
                    len(df) for df in kag_openai_langchain_agent.db_data.values()
                ),
                "vectors_built": hasattr(
                    kag_openai_langchain_agent, "knowledge_vectors"
                )
                and kag_openai_langchain_agent.knowledge_vectors is not None,
                "vector_dimensions": kag_openai_langchain_agent.knowledge_vectors.shape
                if kag_openai_langchain_agent.knowledge_vectors is not None
                else None,
                "test_retrieval_results": len(test_knowledge),
            },
            "langchain_chains": list(kag_openai_langchain_agent.langchain_chains.keys())
            if kag_openai_langchain_agent.langchain_chains
            else [],
            "configuration": {
                "model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.3")),
                "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "1500")),
                "similarity_threshold": float(
                    os.getenv("KNOWLEDGE_SIMILARITY_THRESHOLD", "0.01")
                ),
            },
        }
    except Exception as e:
        logger.error(f"System status error: {e}")
        return {"system_health": f"Error: {str(e)}", "error_details": str(e)}

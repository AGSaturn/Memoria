from .Manager import MemoryManager
from .store.episodic_store import EpisodicStore
from .store.semantic_store import SemanticStore
from .policy.default_policy import DefaultPolicy
from .processor.default_processor import DefaultProcessor
from .vector_index import VectorIndex

class MemoryFactory:
    @staticmethod
    def create_manager(db_path: str = "memoria.db", openai_client = None):
        """
        Creates a fully initialized MemoryManager with all dependencies.
        """
        # 1. Stores
        episodic_store = EpisodicStore(db_path)
        semantic_store = SemanticStore(db_path)
        
        # 2. Processor & Index
        # Assuming DefaultProcessor handles embeddings via openai_client
        processor = DefaultProcessor(llm_client=openai_client)
        vector_index = VectorIndex()
        
        # 3. Policy
        policy = DefaultPolicy()
        
        # 4. Manager
        manager = MemoryManager(
            policy=policy,
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            vector_index=vector_index,
            processor=processor
        )
        
        return manager

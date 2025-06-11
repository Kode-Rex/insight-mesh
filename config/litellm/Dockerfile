FROM ghcr.io/berriai/litellm:main-latest

# Install fastmcp for the RAG hook
RUN pip install fastmcp==2.7.0

# The rag_pipeline will be mounted as a volume at runtime
# This ensures the RAG hook has access to fastmcp dependency 
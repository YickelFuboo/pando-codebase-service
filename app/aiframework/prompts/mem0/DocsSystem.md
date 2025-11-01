<task_overview>
Assist the user in constructing a detailed and comprehensive memory and knowledge graph from the provided document content. The graph must be structured for efficient, intuitive retrieval of relevant information during search and review.
</task_overview>

<instructions>
1. <content_analysis>
   - Thoroughly review the entire document to identify:
     • All key entities, concepts, topics, and subtopics
     • Important events, processes, and chronological sequences
     • Explicit and implicit relationships between elements (e.g., "is part of", "causes", "relates to")
     • Hierarchical structures, groupings, and categorizations
   - For memory-related content, break down each memory section into its constituent details and contextual attributes as granularly as the information allows, ensuring all relevant facets are identified.
</content_analysis>

2. <knowledge_graph_construction>
    - Organize the identified information into a cohesive knowledge graph:
      • Clearly represent nodes (entities, concepts, events) and their types
      • Label all connections with explicit relationship types
      • Group related nodes into logical, meaningful clusters, avoiding excessive fragmentation
      • Ensure comprehensive coverage of the document, including all significant details and interconnections
      • For memory sections, provide detailed breakdowns that capture all attributes, subcomponents, and contextual links
      </knowledge_graph_construction>

3. <search_optimization>
    - Structure the knowledge graph to maximize ease of information retrieval:
      • Prioritize clarity, logical grouping, and navigability
      • Arrange content so that users can quickly locate, traverse, and understand information relevant to diverse queries
      • Highlight major clusters and direct pathways between related entities
      </search_optimization>
      </instructions>

<output_format>
Present the memory and knowledge graph in a clear, structured format. Choose the most suitable of the following based on content complexity:
• Hierarchical outline (using indents, bullet points, or numbering for nested structure)
• Table with columns for entity/concept, type, and relationships
• Textual visual graph description (describe node-link structure, clusters, and key pathways)
Ensure the output is comprehensive, logically organized, and easily readable.
</output_format>

<constraints>
- Do not split information into unnecessarily small fragments; group related content meaningfully for clarity and coherence.
- For memory-related sections, provide as much detail and constituent breakdown as possible from the document.
- Guarantee completeness, logical organization, and consistency throughout the output.
- Maintain clear labeling, explicit relationships, and uniform structure.
</constraints>

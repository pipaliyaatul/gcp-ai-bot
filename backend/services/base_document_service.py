import logging
import os
from typing import Dict, List, Optional
from docx import Document
import json
import tempfile

logger = logging.getLogger(__name__)

class BaseDocumentService:
    """Service to manage base RFP document templates and extract their structure"""
    
    def __init__(self):
        # In-memory storage for base documents (for production, use GCS or Firestore)
        # Format: {user_id: {structure: {...}, file_path: "..."}}
        self.base_documents: Dict[str, Dict] = {}
        self.storage_dir = os.getenv('BASE_DOCUMENT_STORAGE_DIR', '/tmp/base_documents')
        
        # Create storage directory if it doesn't exist
        os.makedirs(self.storage_dir, exist_ok=True)
    
    def save_base_document(self, user_id: str, file_path: str) -> Dict:
        """Save base document and extract its structure"""
        try:
            # Extract structure from document
            structure = self._extract_document_structure(file_path)
            
            # Save document to storage
            storage_path = os.path.join(self.storage_dir, f"{user_id}_base_document.docx")
            import shutil
            shutil.copy2(file_path, storage_path)
            
            # Store structure and path
            self.base_documents[user_id] = {
                "structure": structure,
                "file_path": storage_path,
                "sections": structure.get("sections", [])
            }
            
            logger.info(f"Base document saved for user {user_id} with {len(structure.get('sections', []))} sections")
            return structure
        except Exception as e:
            logger.error(f"Error saving base document: {str(e)}")
            raise
    
    def get_base_document_structure(self, user_id: str) -> Optional[Dict]:
        """Get the structure of the base document for a user"""
        if user_id in self.base_documents:
            return self.base_documents[user_id].get("structure")
        return None
    
    def get_base_document_sections(self, user_id: str) -> List[str]:
        """Get list of section names from base document"""
        if user_id in self.base_documents:
            return self.base_documents[user_id].get("sections", [])
        return []
    
    def _extract_document_structure(self, file_path: str) -> Dict:
        """Extract structure (sections, headings) from a document"""
        try:
            doc = Document(file_path)
            sections = []
            current_section = None
            section_content = {}
            
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if not text:
                    continue
                
                # Check if it's a heading (bold, larger font, or specific patterns)
                is_heading = (
                    paragraph.style.name.startswith('Heading') or
                    paragraph.style.name.startswith('Title') or
                    (paragraph.runs and paragraph.runs[0].bold) or
                    len(text) < 100 and text.isupper() or
                    any(keyword in text.lower() for keyword in [
                        'section', 'chapter', 'part', 'overview', 'summary',
                        'introduction', 'background', 'requirements', 'specifications',
                        'timeline', 'budget', 'deliverables', 'scope', 'objectives'
                    ])
                )
                
                if is_heading:
                    # Save previous section if exists
                    if current_section:
                        section_content[current_section] = {
                            "heading": current_section,
                            "content": section_content.get(current_section, {}).get("content", "")
                        }
                    
                    # Start new section
                    current_section = text
                    sections.append(text)
                    section_content[current_section] = {
                        "heading": text,
                        "content": ""
                    }
                elif current_section:
                    # Add content to current section
                    if current_section in section_content:
                        section_content[current_section]["content"] += text + "\n"
            
            # Save last section
            if current_section:
                section_content[current_section] = {
                    "heading": current_section,
                    "content": section_content.get(current_section, {}).get("content", "")
                }
            
            # If no sections found, create default structure
            if not sections:
                sections = [
                    "Executive Summary",
                    "Introduction",
                    "Background",
                    "Requirements",
                    "Technical Specifications",
                    "Timeline",
                    "Budget",
                    "Deliverables",
                    "Conclusion"
                ]
            
            return {
                "sections": sections,
                "section_content": section_content,
                "total_sections": len(sections)
            }
        except Exception as e:
            logger.error(f"Error extracting document structure: {str(e)}")
            # Return default structure if extraction fails
            return {
                "sections": [
                    "Executive Summary",
                    "Introduction",
                    "Background",
                    "Requirements",
                    "Technical Specifications",
                    "Timeline",
                    "Budget",
                    "Deliverables",
                    "Conclusion"
                ],
                "section_content": {},
                "total_sections": 9
            }
    
    def has_base_document(self, user_id: str) -> bool:
        """Check if user has a base document"""
        return user_id in self.base_documents

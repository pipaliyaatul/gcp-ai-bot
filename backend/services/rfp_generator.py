import logging
import os
from typing import Optional
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

logger = logging.getLogger(__name__)

class RFPGenerator:
    """Generates RFP summary documents based on extracted content"""
    
    def __init__(self):
        # You can integrate with OpenAI, Vertex AI, or other LLM services here
        self.use_ai = os.getenv("USE_AI_FOR_RFP", "true").lower() == "true"
    
    async def generate_rfp_summary(self, extracted_text: str) -> Document:
        """Generate RFP summary document from extracted text"""
        try:
            # Create a new Document
            doc = Document()
            
            # Add title
            title = doc.add_heading('RFP Summary Document', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Add metadata section
            doc.add_heading('Document Information', level=1)
            doc.add_paragraph(f'Generated from: User uploaded content')
            doc.add_paragraph(f'Content length: {len(extracted_text)} characters')
            
            # Add executive summary
            doc.add_heading('Executive Summary', level=1)
            summary_text = self._generate_summary_text(extracted_text)
            doc.add_paragraph(summary_text)
            
            # Add key requirements section
            doc.add_heading('Key Requirements', level=1)
            requirements = self._extract_requirements(extracted_text)
            for req in requirements:
                p = doc.add_paragraph(req, style='List Bullet')
            
            # Add technical specifications
            doc.add_heading('Technical Specifications', level=1)
            tech_specs = self._extract_technical_specs(extracted_text)
            for spec in tech_specs:
                p = doc.add_paragraph(spec, style='List Bullet')
            
            # Add timeline and milestones
            doc.add_heading('Timeline and Milestones', level=1)
            timeline_text = self._extract_timeline_info(extracted_text)
            doc.add_paragraph(timeline_text if timeline_text else "Timeline information to be determined based on project requirements.")
            
            # Add budget considerations
            doc.add_heading('Budget Considerations', level=1)
            budget_text = self._extract_budget_info(extracted_text)
            doc.add_paragraph(budget_text if budget_text else "Budget information to be discussed during proposal evaluation.")
            
            # Add compliance and standards
            doc.add_heading('Compliance and Standards', level=1)
            compliance_text = self._generate_compliance_section(extracted_text)
            doc.add_paragraph(compliance_text)
            
            # Add next steps
            doc.add_heading('Recommended Next Steps', level=1)
            next_steps = [
                "Review and validate all requirements with stakeholders",
                "Prepare detailed technical proposal",
                "Identify resource requirements and team composition",
                "Develop project timeline and milestones",
                "Prepare cost estimate and budget breakdown",
                "Submit proposal by specified deadline"
            ]
            for step in next_steps:
                doc.add_paragraph(step, style='List Number')
            
            return doc
        except Exception as e:
            logger.error(f"Error generating RFP summary: {str(e)}")
            raise
    
    def _generate_summary_text(self, text: str) -> str:
        """Generate executive summary from extracted text"""
        # In a production system, you'd use an LLM here
        # For now, we'll create a structured summary
        words = text.split()
        word_count = len(words)
        
        summary = f"""
        This document provides a comprehensive summary of the Request for Proposal (RFP) requirements 
        based on the uploaded content. The source material contains approximately {word_count} words 
        of detailed information that has been analyzed to extract key project requirements, 
        technical specifications, and compliance standards.
        
        The following sections provide a structured breakdown of the RFP requirements to assist 
        in preparing a comprehensive proposal response.
        """
        return summary.strip()
    
    def _extract_requirements(self, text: str) -> list:
        """Extract key requirements from text"""
        # Simple keyword-based extraction (in production, use NLP/LLM)
        requirements = []
        text_lower = text.lower()
        
        # Look for requirement indicators
        requirement_keywords = ['must', 'required', 'shall', 'should', 'need', 'requirement']
        sentences = text.split('.')
        
        for sentence in sentences[:20]:  # Limit to first 20 sentences
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in requirement_keywords):
                if len(sentence.strip()) > 20:  # Filter out very short sentences
                    requirements.append(sentence.strip())
        
        # If no requirements found, add default
        if not requirements:
            requirements = [
                "All requirements must be clearly documented and validated",
                "Technical specifications must meet industry standards",
                "Compliance with security and data protection regulations is mandatory"
            ]
        
        return requirements[:10]  # Limit to 10 requirements
    
    def _extract_technical_specs(self, text: str) -> list:
        """Extract technical specifications from text"""
        specs = []
        text_lower = text.lower()
        
        # Look for technical indicators
        tech_keywords = ['api', 'database', 'server', 'cloud', 'security', 'integration', 'platform']
        sentences = text.split('.')
        
        for sentence in sentences[:20]:
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in tech_keywords):
                if len(sentence.strip()) > 20:
                    specs.append(sentence.strip())
        
        if not specs:
            specs = [
                "Technical architecture must be scalable and secure",
                "Integration with existing systems must be seamless",
                "Cloud-based solutions preferred"
            ]
        
        return specs[:10]
    
    def _extract_timeline_info(self, text: str) -> Optional[str]:
        """Extract timeline information from text"""
        timeline_keywords = ['deadline', 'timeline', 'schedule', 'milestone', 'delivery', 'due date']
        text_lower = text.lower()
        
        sentences = text.split('.')
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in timeline_keywords):
                if len(sentence.strip()) > 20:
                    return sentence.strip()
        
        return None
    
    def _extract_budget_info(self, text: str) -> Optional[str]:
        """Extract budget information from text"""
        budget_keywords = ['budget', 'cost', 'price', 'funding', 'financial', 'payment']
        text_lower = text.lower()
        
        sentences = text.split('.')
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in budget_keywords):
                if len(sentence.strip()) > 20:
                    return sentence.strip()
        
        return None
    
    def _generate_compliance_section(self, text: str) -> str:
        """Generate compliance and standards section"""
        return """
        All proposals must comply with industry-standard security practices, data protection 
        regulations (including GDPR, HIPAA where applicable), and accessibility standards. 
        The solution must adhere to best practices for software development, testing, and 
        deployment. Documentation and code quality standards must be maintained throughout 
        the project lifecycle.
        """.strip()
    
    async def chat_with_agent(self, message: str) -> str:
        """Chat with AI agent (placeholder - integrate with your AI service)"""
        # In production, integrate with Vertex AI, OpenAI, or other LLM services
        responses = {
            "hello": "Hello! I'm here to help you with RFP analysis and document generation.",
            "help": "I can help you upload files (PDF, DOCX, TXT, or audio files) and generate RFP summaries. Try uploading a file to get started!",
        }
        
        message_lower = message.lower()
        for key, response in responses.items():
            if key in message_lower:
                return response
        
        return f"I understand you said: '{message}'. I'm an AI assistant specialized in RFP analysis. Upload a file to generate a comprehensive RFP summary document."


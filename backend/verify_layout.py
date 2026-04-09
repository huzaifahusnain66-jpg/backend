import os
import sys
from flask import Flask
from app.factory import create_app
from app.extensions import db
from app.models.user import User
from app.models.assignment import Assignment, AssignmentStatus
from app.services.text_generation_service import GeneratedContent, GeneratedSection
from app.services.image_generation_service import GeneratedImage
from app.services.document_service import DocumentService
from config.settings import get_settings

def verify():
    app = create_app()
    with app.app_context():
        # 1. Create a dummy user if not exists
        user = User.query.filter_by(email="test@example.com").first()
        if not user:
            user = User(name="Test User", email="test@example.com")
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
            print(f"Created test user: {user.id}")
        else:
            print(f"Using existing test user: {user.id}")

        # 2. Prepare dummy content
        content = GeneratedContent(
            title="Testing Layout and Templates",
            introduction="This is a test introduction to verify if different layouts and templates work correctly in the AI Assignment Generator.",
            sections=[
                GeneratedSection(
                    title="Section 1: The First Part",
                    content="This is the content of the first section. It should be rendered according to the selected layout.",
                    order=1,
                    image_prompt="A test image prompt"
                ),
                GeneratedSection(
                    title="Section 2: The Second Part",
                    content="This is the content of the second section. We are testing how multiple sections look.",
                    order=2,
                    image_prompt="Another test image prompt"
                )
            ],
            conclusion="This is the conclusion of our test. If you see this in the generated files, the system is working.",
            references=["[1] Test Reference 1", "[2] Test Reference 2"]
        )
        
        images = [] # No actual images for this test

        doc_gen = DocumentService(storage_path=os.path.join(app.root_path, "..", "storage", "documents"))
        
        # 3. Test multiple combinations
        combinations = [
            ("professional", "standard"),
            ("academic", "modern_split"),
            ("modern", "magazine")
        ]
        
        for template, layout in combinations:
            print(f"\n--- Testing Template: {template}, Layout: {layout} ---")
            
            # Create assignment record
            assignment = Assignment(
                user_id=user.id,
                topic=f"Test {template} {layout}",
                template=template,
                layout=layout,
                status=AssignmentStatus.COMPLETED.value
            )
            db.session.add(assignment)
            db.session.commit()
            
            # Generate files
            try:
                docx_path = doc_gen.generate_docx(
                    content=content,
                    images=images,
                    template=template,
                    layout=layout,
                    assignment_id=assignment.id,
                    student_name="Test Student",
                    roll_number="12345",
                    department="Computer Science"
                )
                pdf_path = doc_gen.generate_pdf(
                    content=content,
                    images=images,
                    template=template,
                    layout=layout,
                    assignment_id=assignment.id,
                    student_name="Test Student",
                    roll_number="12345",
                    department="Computer Science"
                )
                
                print(f"SUCCESS: Generated DOCX: {docx_path}")
                print(f"SUCCESS: Generated PDF: {pdf_path}")
                
                # Update record
                assignment.docx_path = docx_path
                assignment.pdf_path = pdf_path
                db.session.commit()
                
            except Exception as e:
                print(f"FAILED for {template}/{layout}: {str(e)}")

if __name__ == "__main__":
    # Ensure storage exists
    os.makedirs("/home/ubuntu/ai-assignment-generator/Backend/storage/documents", exist_ok=True)
    os.makedirs("/home/ubuntu/ai-assignment-generator/Backend/storage/images", exist_ok=True)
    verify()

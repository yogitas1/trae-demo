#!/usr/bin/env python3
"""
Content Enhancer with Gemini 2.5 Pro
Processes files provided by user, enhances content with AI, and saves to knowledge base.
"""

import json
import os
import sys
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import argparse

try:
    from dotenv import load_dotenv
    import google.generativeai as genai
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("Install with: pip install google-generativeai python-dotenv")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Import store_in_jsonl function from conjurer
def store_in_jsonl(summary: str, original_content: str, session_info: dict):
    """Store the summary and metadata in a JSONL file"""
    jsonl_file = Path("session_summaries.jsonl")
    
    entry = {
        "content": summary,
        "metadata": {
            "original_content": original_content,
            "session_id": session_info.get("session_id"),
            "command": session_info.get("command"),
            "started_at": session_info.get("started_at"),
            "ended_at": session_info.get("ended_at"),
            "exit_code": session_info.get("exit_code"),
            "duration_sec": session_info.get("duration_sec")
        }
    }
    
    with jsonl_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def iso_now():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")

class ContentEnhancer:
    def __init__(self, api_key: str = None, model_name: str = "gemini-2.5-flash"):
        """Initialize the content enhancer with Gemini API."""
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable or api_key parameter required")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)
        
    def enhance_content(self, file_content: str, file_path: str) -> Dict[str, Any]:
        """Enhance file content using Gemini 2.5 Pro."""
        prompt = f"""
        Understand the conversation/content in the file {file_path}. 
        List out things that have been updated in the code and changed.
        
        File content:
        {file_content}
        
        Please provide a clear analysis of what this content contains and what changes or updates are evident.
        """
        
        try:
            response = self.model.generate_content(prompt)
            analysis = response.text.strip()
            
            return {
                "analysis": analysis,
                "original_content": file_content,
                "file_path": file_path,
                "processed_at": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error enhancing content: {e}")
            return {
                "analysis": f"Error processing {file_path}: {str(e)}",
                "original_content": file_content,
                "file_path": file_path,
                "processed_at": datetime.now().isoformat()
            }
    
    def create_session_info(self, file_path: str) -> Dict[str, Any]:
        """Create session info for storage."""
        return {
            "session_id": str(uuid.uuid4()),
            "command": f"content_enhancer.py {file_path}",
            "started_at": iso_now(),
            "ended_at": iso_now(),
            "exit_code": 0,
            "duration_sec": 0
        }
    
    def process_file(self, file_path: str) -> bool:
        """Process a single file."""
        try:
            path = Path(file_path)
            if not path.exists():
                print(f"❌ File not found: {file_path}")
                return False
            
            print(f"📂 Processing: {file_path}")
            
            # Read file content
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Try binary files
                with open(path, 'rb') as f:
                    content = f.read().decode('utf-8', errors='ignore')
            
            # Enhance content with Gemini
            print(f"🤖 Enhancing with Gemini 2.5 Pro...")
            enhanced_data = self.enhance_content(content, str(path))
            
            # Create session info and store using conjurer's format
            session_info = self.create_session_info(str(path))
            store_in_jsonl(enhanced_data["analysis"], content, session_info)
            print(f"✓ Saved to session_summaries.jsonl")
            
            return True
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(
        description="Enhance file content with Gemini 2.5 Pro and save to knowledge base"
    )
    parser.add_argument(
        "files", 
        nargs="*",
        help="Files to process (if none provided, will prompt for input)"
    )
    parser.add_argument(
        "--api-key",
        help="Gemini API key (or set GEMINI_API_KEY environment variable)"
    )
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash",
        help="Gemini model to use (default: gemini-2.5-flash)"
    )
    
    args = parser.parse_args()
    
    try:
        enhancer = ContentEnhancer(api_key=args.api_key, model_name=args.model)
        
        # If no files provided via command line, prompt for input
        if not args.files:
            print("📝 Enter file paths (one per line, empty line to finish):")
            files_to_process = []
            while True:
                file_path = input("File path: ").strip()
                if not file_path:
                    break
                files_to_process.append(file_path)
        else:
            files_to_process = args.files
        
        if not files_to_process:
            print("❌ No files to process")
            return
        
        print(f"\n🚀 Starting processing of {len(files_to_process)} files...")
        
        success_count = 0
        for file_path in files_to_process:
            if enhancer.process_file(file_path):
                success_count += 1
            print()  # Empty line for readability
        
        print(f"✅ Completed! Successfully processed {success_count}/{len(files_to_process)} files")
        print(f"📊 Knowledge base saved to: session_summaries.jsonl")
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()